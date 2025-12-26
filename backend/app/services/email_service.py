"""
Servicio de correo electrónico.
Envía notificaciones y PDFs firmados a los usuarios.
"""
import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, List
import os

from ..core.config import settings, get_colombia_time

# Configure logger
logger = logging.getLogger(__name__)


class EmailService:
    """
    Servicio de envío de correos electrónicos.
    Soporta SMTP con TLS para mayor seguridad.
    """
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_TLS
        self.enabled = settings.EMAIL_ENABLED
    
    def is_configured(self) -> bool:
        """Verifica si el servicio de email está configurado correctamente."""
        return bool(self.enabled and self.host and self.user and self.password)
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: Optional[List[dict]] = None
    ) -> MIMEMultipart:
        """Crea un mensaje de correo con formato HTML y adjuntos opcionales."""
        message = MIMEMultipart('mixed')
        message['From'] = f"{self.from_name} <{self.from_email}>"
        message['To'] = to_email
        message['Subject'] = subject
        
        # Cuerpo del mensaje en HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # Adjuntos
        if attachments:
            for attachment in attachments:
                filename = attachment.get('filename', 'documento.pdf')
                content = attachment.get('content')
                content_type = attachment.get('content_type', 'application/pdf')
                
                if content:
                    part = MIMEApplication(content, Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    message.attach(part)
        
        return message
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Envía un correo electrónico de forma síncrona.
        
        Args:
            to_email: Dirección de correo del destinatario
            subject: Asunto del correo
            html_content: Contenido HTML del correo
            attachments: Lista de diccionarios con {filename, content, content_type}
        
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.is_configured():
            logger.warning("Email service not configured. Skipping email send.")
            return False
        
        try:
            message = self._create_message(to_email, subject, html_content, attachments)
            
            if self.use_tls:
                # Conexión con STARTTLS
                context = ssl.create_default_context()
                with smtplib.SMTP(self.host, self.port) as server:
                    server.starttls(context=context)
                    server.login(self.user, self.password)
                    server.send_message(message)
            else:
                # Conexión SSL directa
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    server.login(self.user, self.password)
                    server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def send_registration_email(
        self,
        to_email: str,
        full_name: str,
        person_type: str,
        document_type: str,
        document_number: str,
        company_name: Optional[str] = None,
        nit: Optional[str] = None,
        municipality_name: Optional[str] = None
    ) -> bool:
        """
        Envía correo de bienvenida al nuevo usuario registrado.
        """
        colombia_time = get_colombia_time()
        date_str = colombia_time.strftime('%d/%m/%Y %H:%M:%S')
        
        if person_type == 'juridica':
            subject = f"Bienvenido al Sistema ICA - {company_name}"
            user_info = f"""
                <tr><td><strong>Empresa:</strong></td><td>{company_name}</td></tr>
                <tr><td><strong>NIT:</strong></td><td>{nit}</td></tr>
                <tr><td><strong>Representante Legal:</strong></td><td>{full_name}</td></tr>
                <tr><td><strong>Tipo de Documento:</strong></td><td>{document_type}</td></tr>
                <tr><td><strong>Número de Documento:</strong></td><td>{document_number}</td></tr>
            """
        else:
            subject = f"Bienvenido al Sistema ICA - {full_name}"
            user_info = f"""
                <tr><td><strong>Nombre:</strong></td><td>{full_name}</td></tr>
                <tr><td><strong>Tipo de Documento:</strong></td><td>{document_type}</td></tr>
                <tr><td><strong>Número de Documento:</strong></td><td>{document_number}</td></tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #e9ecef; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .info-table td {{ padding: 8px; border-bottom: 1px solid #e9ecef; }}
                .info-table td:first-child {{ width: 40%; color: #666; }}
                .footer {{ background: #e9ecef; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
                .btn {{ display: inline-block; background: #e94560; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Sistema ICA</h1>
                    <p>Formulario Único Nacional de Declaración y Pago</p>
                </div>
                <div class="content">
                    <h2>¡Bienvenido(a) al Sistema ICA!</h2>
                    <p>Su cuenta ha sido creada exitosamente. A continuación encontrará los datos de su registro:</p>
                    
                    <table class="info-table">
                        {user_info}
                        <tr><td><strong>Correo Electrónico:</strong></td><td>{to_email}</td></tr>
                        <tr><td><strong>Municipio:</strong></td><td>{municipality_name or 'No asignado'}</td></tr>
                        <tr><td><strong>Fecha de Registro:</strong></td><td>{date_str} (Hora Colombia)</td></tr>
                    </table>
                    
                    <p>Ya puede acceder al sistema para realizar sus declaraciones del Impuesto de Industria y Comercio (ICA).</p>
                    
                    <p><strong>Recuerde:</strong></p>
                    <ul>
                        <li>Guarde sus credenciales de acceso en un lugar seguro.</li>
                        <li>No comparta su contraseña con terceros.</li>
                        <li>Si olvida su contraseña, contacte al administrador del sistema.</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>Este es un correo automático, por favor no responda a este mensaje.</p>
                    <p>© {colombia_time.year} Sistema ICA - Todos los derechos reservados</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_signed_form_email(
        self,
        to_email: str,
        full_name: str,
        form_number: str,
        filing_number: str,
        tax_year: int,
        amount_to_pay: float,
        pdf_path: str,
        municipality_name: Optional[str] = None
    ) -> bool:
        """
        Envía el formulario firmado por correo electrónico.
        """
        colombia_time = get_colombia_time()
        date_str = colombia_time.strftime('%d/%m/%Y %H:%M:%S')
        
        # Formatear monto
        amount_formatted = f"${amount_to_pay:,.0f}" if amount_to_pay else "$0"
        
        subject = f"Declaración ICA Firmada - Radicado {filing_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #e9ecef; }}
                .info-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                .info-table td {{ padding: 10px; border-bottom: 1px solid #e9ecef; }}
                .info-table td:first-child {{ width: 40%; color: #666; font-weight: bold; }}
                .highlight {{ background: #dcfce7; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #059669; }}
                .footer {{ background: #e9ecef; padding: 15px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }}
                .badge {{ display: inline-block; background: #059669; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Declaración Firmada Exitosamente</h1>
                    <p>Formulario Único Nacional de Declaración y Pago ICA</p>
                </div>
                <div class="content">
                    <p>Estimado(a) <strong>{full_name}</strong>,</p>
                    
                    <p>Su declaración del Impuesto de Industria y Comercio (ICA) ha sido firmada y radicada correctamente.</p>
                    
                    <div class="highlight">
                        <p style="margin: 0;"><span class="badge">RADICADO</span></p>
                        <h2 style="margin: 10px 0 0 0; color: #059669;">{filing_number}</h2>
                    </div>
                    
                    <table class="info-table">
                        <tr><td>Número de Formulario:</td><td>{form_number}</td></tr>
                        <tr><td>Año Gravable:</td><td>{tax_year}</td></tr>
                        <tr><td>Municipio:</td><td>{municipality_name or 'No especificado'}</td></tr>
                        <tr><td>Valor Total a Pagar:</td><td><strong>{amount_formatted}</strong></td></tr>
                        <tr><td>Fecha de Radicación:</td><td>{date_str} (Hora Colombia)</td></tr>
                    </table>
                    
                    <p><strong>📎 Adjunto:</strong> Encontrará el PDF de su declaración firmada adjunto a este correo. 
                    Guárdelo como soporte oficial de su declaración.</p>
                    
                    <p style="background: #fef3c7; padding: 10px; border-radius: 5px; border-left: 4px solid #f59e0b;">
                        <strong>⚠️ Importante:</strong> Este documento tiene validez legal. Consérvelo para cualquier 
                        trámite futuro ante la autoridad tributaria municipal.
                    </p>
                </div>
                <div class="footer">
                    <p>Este es un correo automático, por favor no responda a este mensaje.</p>
                    <p>© {colombia_time.year} Sistema ICA - Todos los derechos reservados</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Leer el PDF adjunto
        attachments = []
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                attachments.append({
                    'filename': f'Declaracion_ICA_{filing_number}.pdf',
                    'content': pdf_content,
                    'content_type': 'application/pdf'
                })
            except Exception as e:
                logger.warning(f"Could not read PDF file: {e}")
        
        return self.send_email(to_email, subject, html_content, attachments)


# Singleton instance
email_service = EmailService()
