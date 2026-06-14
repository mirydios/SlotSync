import logging
from datetime import datetime, timedelta
import asyncio
from app.database import SessionLocal
from app.models.booking import Booking
from app.services.email import send_raw_email

logger = logging.getLogger(__name__)

async def send_reminder_emails():
    """
    Checks for bookings starting in the next 24 hours that haven't had a reminder sent.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        twenty_four_hours_from_now = now + timedelta(hours=24)
        
        # Find bookings between now and 24h from now
        upcoming_bookings = db.query(Booking).filter(
            Booking.status == "confirmed",
            Booking.reminder_sent == False,
            Booking.start_datetime > now,
            Booking.start_datetime <= twenty_four_hours_from_now
        ).all()

        for booking in upcoming_bookings:
            owner = booking.public_link.owner
            fmt = "%d/%m/%Y às %H:%M"
            start_str = booking.start_datetime.strftime(fmt)

            try:
                # To Guest
                await send_raw_email(
                    to_email=booking.guest_email,
                    subject=f"Lembrete: Reunião com {owner.name} amanhã",
                    body=f"""
                    Olá {booking.guest_name},
                    
                    Este é um lembrete automático de que você tem uma reunião amanhã!
                    
                    Com: {owner.name} ({owner.email})
                    Data/Hora: {start_str}
                    
                    Se precisar reagendar ou cancelar, verifique o e-mail de confirmação original.
                    """
                )
                
                # To Owner
                await send_raw_email(
                    to_email=owner.email,
                    subject=f"Lembrete: Reunião com {booking.guest_name} amanhã",
                    body=f"""
                    Olá {owner.name},
                    
                    Lembrete da sua reunião amanhã.
                    
                    Convidado: {booking.guest_name} ({booking.guest_email})
                    Data/Hora: {start_str}
                    Notas: {booking.guest_notes or 'Nenhuma'}
                    """
                )
                
                # Mark as sent
                booking.reminder_sent = True
                db.commit()
                logger.info(f"Reminders sent for booking {booking.id}")
                
            except Exception as e:
                logger.error(f"Failed to send reminders for booking {booking.id}: {e}")
                
    finally:
        db.close()

def run_reminders_sync():
    """Wrapper to run async function from APScheduler sync job"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_reminder_emails())
    except RuntimeError:
        asyncio.run(send_reminder_emails())
