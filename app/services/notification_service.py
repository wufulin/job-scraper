from __future__ import annotations

import math
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import asyncpg
from loguru import logger

from app.config.settings import settings
from app.models.responses import (
    NotificationListResponse,
    NotificationResponse,
    PaginationMeta,
    UnreadCountResponse,
)


class NotificationService:

    def __init__(self, pool: Optional[asyncpg.Pool] = None) -> None:
        self._pool = pool

    def _assert_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Pool not initialized")
        return self._pool

    async def get_notifications(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
    ) -> NotificationListResponse:
        pool = self._assert_pool()

        where = "WHERE user_id = $1"
        params: list = [user_id]
        if unread_only:
            where += " AND is_read = false"

        total = await pool.fetchval(
            f"SELECT COUNT(*) FROM notifications {where}", *params
        )

        total_pages = max(1, math.ceil(total / per_page))
        offset = (page - 1) * per_page

        rows = await pool.fetch(
            f"SELECT id, user_id, type, title, body, job_id, is_read, email_sent, created_at "
            f"FROM notifications {where} ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
            *params,
            per_page,
            offset,
        )

        notifications = [
            NotificationResponse(
                id=str(row["id"]),
                user_id=str(row["user_id"]),
                type=row["type"],
                title=row["title"],
                body=row["body"],
                job_id=row["job_id"],
                is_read=row["is_read"],
                email_sent=row["email_sent"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return NotificationListResponse(
            data=notifications,
            pagination=PaginationMeta(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def get_unread_count(self, user_id: str) -> UnreadCountResponse:
        pool = self._assert_pool()
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND is_read = false",
            user_id,
        )
        return UnreadCountResponse(count=count)

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        pool = self._assert_pool()
        result = await pool.execute(
            "UPDATE notifications SET is_read = true WHERE id = $1 AND user_id = $2",
            notification_id,
            user_id,
        )
        return result == "UPDATE 1"

    async def mark_all_read(self, user_id: str) -> int:
        pool = self._assert_pool()
        result = await pool.execute(
            "UPDATE notifications SET is_read = true WHERE user_id = $1 AND is_read = false",
            user_id,
        )
        try:
            return int(result.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        body: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> NotificationResponse:
        pool = self._assert_pool()
        row = await pool.fetchrow(
            "INSERT INTO notifications (user_id, type, title, body, job_id) "
            "VALUES ($1, $2, $3, $4, $5) "
            "RETURNING id, user_id, type, title, body, job_id, is_read, email_sent, created_at",
            user_id,
            type,
            title,
            body,
            job_id,
        )
        return NotificationResponse(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            type=row["type"],
            title=row["title"],
            body=row["body"],
            job_id=row["job_id"],
            is_read=row["is_read"],
            email_sent=row["email_sent"],
            created_at=row["created_at"],
        )

    def send_email_notification(
        self,
        to_email: str,
        notification: NotificationResponse,
    ) -> bool:
        if not settings.SMTP_HOST or not settings.FROM_EMAIL:
            logger.debug("SMTP not configured — skipping email")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = notification.title
        msg["From"] = settings.FROM_EMAIL
        msg["To"] = to_email

        text_body = notification.body or notification.title
        html_body = f"<html><body><p>{text_body}</p></body></html>"
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
            logger.info("Email sent to {}", to_email)
            return True
        except Exception:
            logger.exception("Failed to send email to {}", to_email)
            return False

    async def check_subscriptions_after_scrape(
        self,
        new_jobs: list[dict],
    ) -> int:
        """Match new jobs against all active subscriptions and create notifications.

        Args:
            new_jobs: List of job dicts with keys: id, title, description, source, company.

        Returns:
            Total number of notifications created.
        """
        pool = self._assert_pool()

        rows = await pool.fetch(
            "SELECT id, user_id, keywords, match_mode, sources "
            "FROM subscriptions WHERE is_active = true"
        )

        if not rows:
            return 0

        total_created = 0

        for sub_row in rows:
            keywords = sub_row["keywords"] or []
            match_mode = sub_row["match_mode"] or "any"
            sources = sub_row["sources"] or []
            user_id = str(sub_row["user_id"])

            if not keywords:
                continue

            compiled = [
                re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords
            ]

            for job in new_jobs:
                if sources and job.get("source") not in sources:
                    continue

                text = " ".join(
                    filter(None, [job.get("title", ""), job.get("description", "")])
                )

                if not text:
                    continue

                if match_mode == "all":
                    matched = all(p.search(text) for p in compiled)
                else:
                    matched = any(p.search(text) for p in compiled)

                if matched:
                    company = job.get("company") or "Unknown"
                    title_text = f"New match: {job.get('title', 'Untitled')}"
                    body_text = f"{company} — {job.get('title', '')}"

                    await self.create_notification(
                        user_id=user_id,
                        type="new_match",
                        title=title_text,
                        body=body_text,
                        job_id=job.get("id"),
                    )
                    total_created += 1

        logger.info(
            "Subscription check complete — {} notification(s) created", total_created
        )
        return total_created
