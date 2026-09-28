"""Email notification delivery service for AI Disaster Response Coordinator via Resend.

Dispatches structured communications prepared by CommunicationAgent exclusively
via the Resend Email API. Supports safe DRY_RUN mode (default) and LIVE mode.
Never prints or exposes secrets.
"""

import hashlib
import html
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import resend


class NotificationService:
    """Manages dispatch of prepared emergency communications via Resend Email API.

    Modes:
    - DRY_RUN (default): Safe simulated dispatch. No external networks contacted.
    - LIVE: Real external email dispatch via Resend API.
    - CONSOLE: Formats and logs dispatches to local console.
    """

    DEFAULT_TIMEOUT_SECONDS = 5.0

    def __init__(self, mode: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        if "NOTIFICATION_MODE" not in os.environ:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except Exception:
                pass
        self._explicit_mode = mode.upper() if mode else None
        self.timeout = timeout

    @property
    def mode(self) -> str:
        if self._explicit_mode:
            return self._explicit_mode
        env_mode = os.getenv("NOTIFICATION_MODE", "DRY_RUN").strip().upper()
        if env_mode in ("DRY_RUN", "LIVE", "CONSOLE"):
            return env_mode
        return "DRY_RUN"

    @mode.setter
    def mode(self, val: str):
        self._explicit_mode = val.upper() if val else None

    # -------------------------------------------------------------------------
    # EMAIL DISPATCH LOGIC (Resend Email API)
    # -------------------------------------------------------------------------

    def _dispatch_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        target: str = "operational_alert",
        recipient_name: str = "Unknown",
        priority: str = "NORMAL",
        mission_id: Optional[int] = None,
        reason: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route Email via Resend Email API or simulation."""
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_email = (to_email or "").strip()

        # Missing or invalid recipient
        if not clean_email or "@" not in clean_email:
            return {
                "status": "skipped",
                "message_id": None,
                "target": target,
                "channel": "email",
                "recipient": clean_email or recipient_name or "N/A",
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason or "No usable email address provided.",
                "context": context,
                "error": None,
                "timestamp": now_iso,
            }

        # DRY_RUN mode: Simulated delivery without network calls
        if self.mode == "DRY_RUN":
            seed = f"{clean_email}:{subject}:{time.time()}"
            msg_hash = hashlib.sha256(seed.encode()).hexdigest()[:8]
            return {
                "status": "simulated",
                "message_id": f"sim-resend-{msg_hash}",
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": None,
                "note": "Simulated Email delivery in DRY_RUN mode.",
                "timestamp": now_iso,
            }

        # CONSOLE mode: Simulated delivery with local console logging
        if self.mode == "CONSOLE":
            seed = f"{clean_email}:{subject}:{time.time()}"
            msg_hash = hashlib.sha256(seed.encode()).hexdigest()[:8]
            print(f"[CONSOLE EMAIL] To: {clean_email} | Subject: {subject} | Body: {body[:60]}...")
            return {
                "status": "simulated",
                "message_id": f"console-resend-{msg_hash}",
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": None,
                "note": "Console log output mode.",
                "timestamp": now_iso,
            }

        # LIVE mode via Resend Python SDK
        api_key = (os.getenv("RESEND_API_KEY") or "").strip()
        from_email = (os.getenv("RESEND_EMAIL_FROM") or "").strip()

        if not api_key:
            return {
                "status": "failed",
                "message_id": None,
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": "Resend configuration incomplete: RESEND_API_KEY is missing.",
                "timestamp": now_iso,
            }

        if not from_email:
            return {
                "status": "failed",
                "message_id": None,
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": "Resend configuration incomplete: RESEND_EMAIL_FROM sender address is missing.",
                "timestamp": now_iso,
            }

        escaped_text = html.escape(body)
        html_content = f"<div style='font-family: sans-serif; line-height: 1.5;'><p>{escaped_text.replace(chr(10), '<br>')}</p></div>"
        text_content = body

        try:
            resend.api_key = api_key
            params = {
                "from": from_email,
                "to": [clean_email],
                "subject": subject,
                "html": html_content,
                "text": text_content,
            }
            response = resend.Emails.send(params)

            email_id = None
            if isinstance(response, dict):
                email_id = response.get("id")
            elif hasattr(response, "id"):
                email_id = getattr(response, "id")
            elif hasattr(response, "__getitem__"):
                try:
                    email_id = response["id"]
                except Exception:
                    pass

            msg_id = email_id or f"resend-{int(time.time() * 1000)}"

            return {
                "status": "submitted",
                "message_id": str(msg_id),
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": None,
                "timestamp": now_iso,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "message_id": None,
                "target": target,
                "channel": "email",
                "recipient": clean_email,
                "provider": "resend",
                "subject": subject,
                "message": body,
                "priority": priority,
                "mission_id": mission_id,
                "reason": reason,
                "context": context,
                "error": f"Resend delivery error: {exc.__class__.__name__}: {str(exc)}",
                "timestamp": now_iso,
            }

    # -------------------------------------------------------------------------
    # MAIN BATCH DISPATCH ENTRYPOINT
    # -------------------------------------------------------------------------

    def dispatch_communications(
        self,
        communications: Dict[str, Any],
        alert_email_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatch structured communication payloads generated by CommunicationAgent via Resend.

        Does not require changes to CommunicationAgent.
        All communications are routed exclusively via Email.
        """
        if not isinstance(communications, dict):
            return {
                "dispatch_status": "failed",
                "dispatch_mode": self.mode,
                "email_provider": "RESEND",
                "total_messages": 0,
                "sent": 0,
                "submitted": 0,
                "simulated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
                "error": "Invalid communications payload format.",
            }

        messages = communications.get("messages") or communications.get("communications") or []
        comm_mission_id = communications.get("mission_id")
        results: List[Dict[str, Any]] = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            target = msg.get("target", "unknown")
            contact = str(msg.get("contact") or "").strip()
            recipient_name = str(msg.get("recipient") or "Unknown").strip()
            subject = str(msg.get("subject") or msg.get("title") or "Emergency Advisory").strip()
            body = str(msg.get("message") or "").strip()
            priority = str(msg.get("priority") or "NORMAL").strip()
            reason = msg.get("reason")
            context = msg.get("context")
            mission_id = msg.get("mission_id") or comm_mission_id

            # Determine destination email address
            candidate_email = msg.get("email") or msg.get("recipient_email") or contact

            res = self._dispatch_email(
                to_email=candidate_email,
                subject=subject,
                body=body,
                target=target,
                recipient_name=recipient_name,
                priority=priority,
                mission_id=mission_id,
                reason=reason,
                context=context,
            )
            results.append(res)

        # Operational Alert Email to configured coordinator
        alert_email = (
            alert_email_override
            or os.getenv("RESEND_EMAIL_RECIPIENT")
        )
        if alert_email and str(alert_email).strip():
            target_email = str(alert_email).strip()
            summary_text = communications.get("summary") or "Emergency incident response coordination active."
            subject = f"[EMERGENCY ALERT] Operational Directive - Mission #{comm_mission_id or 'N/A'}"
            email_res = self._dispatch_email(
                to_email=target_email,
                subject=subject,
                body=summary_text,
                target="operational_coordinator",
                recipient_name="Operational Coordinator",
                priority="HIGH",
                mission_id=comm_mission_id,
                reason="Operational summary notification",
                context=f"Mission #{comm_mission_id or 'N/A'} operational overview",
            )
            results.append(email_res)

        total_messages = len(results)
        submitted_count = sum(1 for r in results if r["status"] == "submitted")
        sent_count = submitted_count
        simulated_count = sum(1 for r in results if r["status"] == "simulated")
        failed_count = sum(1 for r in results if r["status"] == "failed")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")

        if self.mode == "DRY_RUN":
            dispatch_status = "dry_run"
        elif failed_count > 0 and submitted_count > 0:
            dispatch_status = "partial"
        elif failed_count > 0 and submitted_count == 0:
            dispatch_status = "failed"
        else:
            dispatch_status = "completed"

        return {
            "dispatch_status": dispatch_status,
            "dispatch_mode": self.mode,
            "email_provider": "RESEND",
            "total_messages": total_messages,
            "sent": sent_count,
            "submitted": submitted_count,
            "simulated": simulated_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "results": results,
        }
