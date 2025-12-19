"""
Servicio de generación de PDF.
Genera PDF institucional basado en el formulario ICA.
Almacena en el filesystem local del servidor (requerimiento on-premise).
"""
import os
from datetime import datetime
from typing import Optional
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from ..core.config import settings, get_pdf_path


class PDFGenerator:
    """
    Generador de PDF para declaraciones ICA.
    Basado en: Documents/formulario-ICA.md
    """
    
    def __init__(self, white_label_config: dict = None):
        """
        Inicializa el generador con configuración marca blanca.
        """
        self.config = white_label_config or {}
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos personalizados."""
        primary_color = self.config.get('primary_color', '#003366')
        font_family = self.config.get('font_family', 'Helvetica')
        
        # Convertir color hex a RGB
        r, g, b = self._hex_to_rgb(primary_color)
        
        self.styles.add(ParagraphStyle(
            name='FormTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.Color(r/255, g/255, b/255),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.Color(r/255, g/255, b/255),
            spaceBefore=15,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.grey
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convierte color hexadecimal a RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def generate_declaration_pdf(
        self,
        declaration_data: dict,
        output_path: Optional[str] = None
    ) -> str:
        """
        Genera el PDF de una declaración ICA.
        
        Args:
            declaration_data: Datos completos de la declaración
            output_path: Ruta de salida (si no se proporciona, se genera automáticamente)
        
        Returns:
            Ruta del archivo PDF generado
        """
        # Determinar ruta de salida
        if not output_path:
            year = declaration_data.get('tax_year', datetime.now().year)
            municipality = declaration_data.get('municipality', {}).get('name', 'default')
            user_id = declaration_data.get('user_id', 0)
            
            base_path = get_pdf_path(year, municipality, user_id)
            os.makedirs(base_path, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            form_number = declaration_data.get('form_number', 'DRAFT')
            output_path = os.path.join(base_path, f"ICA_{form_number}_{timestamp}.pdf")
        
        # Crear documento
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        # Construir contenido
        elements = []
        
        # Header con logo
        elements.extend(self._build_header(declaration_data))
        
        # Título del formulario
        form_title = self.config.get(
            'form_title',
            'Formulario Único Nacional de Declaración y Pago ICA'
        )
        elements.append(Paragraph(form_title, self.styles['FormTitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Metadatos
        elements.extend(self._build_metadata_section(declaration_data))
        
        # Sección A - Contribuyente
        elements.extend(self._build_taxpayer_section(declaration_data.get('taxpayer', {})))
        
        # Sección B - Base Gravable
        elements.extend(self._build_income_section(declaration_data.get('income_base', {})))
        
        # Sección C - Actividades
        elements.extend(self._build_activities_section(declaration_data.get('activities', [])))
        
        # Sección D - Liquidación
        elements.extend(self._build_settlement_section(declaration_data.get('settlement', {})))
        
        # Sección E - Descuentos
        elements.extend(self._build_discounts_section(declaration_data.get('discounts', {})))
        
        # Sección F - Resultado
        elements.extend(self._build_result_section(declaration_data.get('result', {})))
        
        # Sección G - Firma
        elements.extend(self._build_signature_section(declaration_data))
        
        # Footer con notas legales
        elements.extend(self._build_footer())
        
        # Generar PDF
        doc.build(elements)
        
        return output_path
    
    def _build_header(self, data: dict) -> list:
        """Construye el encabezado del PDF."""
        elements = []
        
        # Logo si existe
        logo_path = self.config.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            logo = Image(logo_path, width=2*inch, height=1*inch)
            elements.append(logo)
        
        # Texto de encabezado
        header_text = self.config.get('header_text', '')
        if header_text:
            elements.append(Paragraph(header_text, self.styles['Normal']))
        
        # Información del municipio
        municipality = data.get('municipality', {})
        if municipality:
            muni_text = f"<b>{municipality.get('name', '')}</b> - {municipality.get('department', '')}"
            elements.append(Paragraph(muni_text, self.styles['Normal']))
        
        elements.append(Spacer(1, 0.2*inch))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.grey))
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_metadata_section(self, data: dict) -> list:
        """Construye la sección de metadatos."""
        elements = []
        
        metadata = [
            ['Año Gravable:', str(data.get('tax_year', ''))],
            ['Tipo de Declaración:', data.get('declaration_type', '').replace('_', ' ').title()],
            ['Número de Formulario:', data.get('form_number', '')],
            ['Estado:', data.get('status', '').title()],
        ]
        
        table = Table(metadata, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_taxpayer_section(self, taxpayer: dict) -> list:
        """Construye Sección A - Información del Contribuyente."""
        elements = []
        
        elements.append(Paragraph('Sección A – Información del Contribuyente', self.styles['SectionTitle']))
        
        data = [
            ['Tipo de Documento:', taxpayer.get('document_type', ''),
             'Número:', taxpayer.get('document_number', '')],
            ['DV:', taxpayer.get('verification_digit', ''),
             'Razón Social:', taxpayer.get('legal_name', '')],
            ['Dirección:', taxpayer.get('address', ''),
             'Municipio:', taxpayer.get('municipality', '')],
            ['Departamento:', taxpayer.get('department', ''),
             'Teléfono:', taxpayer.get('phone', '')],
            ['Correo Electrónico:', taxpayer.get('email', ''), '', ''],
        ]
        
        table = Table(data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_income_section(self, income: dict) -> list:
        """Construye Sección B - Base Gravable."""
        elements = []
        
        elements.append(Paragraph('Sección B – Base Gravable', self.styles['SectionTitle']))
        
        # Formatear valores monetarios
        def fmt(value):
            return f"${value:,.2f}" if value else "$0.00"
        
        r8 = income.get('row_8_ordinary_income', 0)
        r9 = income.get('row_9_extraordinary_income', 0)
        r10 = r8 + r9  # Calculado
        r11 = income.get('row_11_returns', 0)
        r12 = income.get('row_12_exports', 0)
        r13 = income.get('row_13_fixed_assets_sales', 0)
        r14 = income.get('row_14_excluded_income', 0)
        r15 = income.get('row_15_non_taxable_income', 0)
        r16 = r10 - (r11 + r12 + r13 + r14 + r15)  # Calculado
        
        data = [
            ['Renglón', 'Concepto', 'Valor'],
            ['8', 'Total ingresos ordinarios', fmt(r8)],
            ['9', 'Ingresos extraordinarios', fmt(r9)],
            ['10', 'TOTAL INGRESOS (Calculado)', fmt(r10)],
            ['11', 'Devoluciones', fmt(r11)],
            ['12', 'Exportaciones', fmt(r12)],
            ['13', 'Ventas de activos fijos', fmt(r13)],
            ['14', 'Ingresos excluidos', fmt(r14)],
            ['15', 'Ingresos no gravados', fmt(r15)],
            ['16', 'TOTAL INGRESOS GRAVABLES (Calculado)', fmt(r16)],
        ]
        
        table = Table(data, colWidths=[0.8*inch, 4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            # Resaltar filas calculadas
            ('BACKGROUND', (0, 3), (-1, 3), colors.Color(0.9, 0.95, 0.9)),
            ('BACKGROUND', (0, 9), (-1, 9), colors.Color(0.9, 0.95, 0.9)),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTNAME', (0, 9), (-1, 9), 'Helvetica-Bold'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_activities_section(self, activities: list) -> list:
        """Construye Sección C - Actividades Gravadas."""
        elements = []
        
        elements.append(Paragraph('Sección C – Actividades Gravadas', self.styles['SectionTitle']))
        
        def fmt(value):
            return f"${value:,.2f}" if value else "$0.00"
        
        data = [['Código CIIU', 'Descripción', 'Ingresos', 'Tarifa (‰)', 'Impuesto']]
        
        total_tax = 0
        for act in activities:
            tax = act.get('income', 0) * act.get('tax_rate', 0) / 1000
            total_tax += tax
            data.append([
                act.get('ciiu_code', ''),
                act.get('description', '')[:40],  # Truncar descripción
                fmt(act.get('income', 0)),
                f"{act.get('tax_rate', 0):.2f}",
                fmt(tax)
            ])
        
        # Fila de total
        data.append(['', 'TOTAL IMPUESTO POR ACTIVIDADES', '', '', fmt(total_tax)])
        
        table = Table(data, colWidths=[1*inch, 2.5*inch, 1.3*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            # Fila de total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_settlement_section(self, settlement: dict) -> list:
        """Construye Sección D - Liquidación del Impuesto."""
        elements = []
        
        elements.append(Paragraph('Sección D – Liquidación del Impuesto', self.styles['SectionTitle']))
        
        def fmt(value):
            return f"${value:,.2f}" if value else "$0.00"
        
        r30 = settlement.get('row_30_ica_tax', 0)
        r31 = settlement.get('row_31_signs_boards', 0)
        r32 = settlement.get('row_32_surcharge', 0)
        r33 = r30 + r31 + r32
        
        data = [
            ['Renglón', 'Concepto', 'Valor'],
            ['30', 'Impuesto de Industria y Comercio', fmt(r30)],
            ['31', 'Avisos y Tableros', fmt(r31)],
            ['32', 'Sobretasa', fmt(r32)],
            ['33', 'TOTAL IMPUESTO (Calculado)', fmt(r33)],
        ]
        
        table = Table(data, colWidths=[0.8*inch, 4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_discounts_section(self, discounts: dict) -> list:
        """Construye Sección E - Descuentos, Créditos y Anticipos."""
        elements = []
        
        elements.append(Paragraph('Sección E – Descuentos, Créditos y Anticipos', self.styles['SectionTitle']))
        
        def fmt(value):
            return f"${value:,.2f}" if value else "$0.00"
        
        d1 = discounts.get('tax_discounts', 0)
        d2 = discounts.get('advance_payments', 0)
        d3 = discounts.get('withholdings', 0)
        total = d1 + d2 + d3
        
        data = [
            ['Concepto', 'Valor'],
            ['Descuentos tributarios', fmt(d1)],
            ['Anticipos pagados', fmt(d2)],
            ['Retenciones sufridas', fmt(d3)],
            ['TOTAL CRÉDITOS', fmt(total)],
        ]
        
        table = Table(data, colWidths=[4.8*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_result_section(self, result: dict) -> list:
        """Construye Sección F - Total a Pagar / Saldo a Favor."""
        elements = []
        
        elements.append(Paragraph('Sección F – Total a Pagar / Saldo a Favor', self.styles['SectionTitle']))
        
        def fmt(value):
            return f"${value:,.2f}" if value else "$0.00"
        
        amount_to_pay = result.get('amount_to_pay', 0)
        balance_in_favor = result.get('balance_in_favor', 0)
        
        data = [
            ['Concepto', 'Valor'],
            ['Total a Pagar', fmt(amount_to_pay)],
            ['Saldo a Favor', fmt(balance_in_favor)],
        ]
        
        table = Table(data, colWidths=[4.8*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_signature_section(self, data: dict) -> list:
        """Construye Sección G - Firma y Responsabilidad."""
        elements = []
        
        elements.append(Paragraph('Sección G – Firma y Responsabilidad', self.styles['SectionTitle']))
        
        # Datos de firma
        signature_info = data.get('signature_info', {})
        
        sig_data = [
            ['Nombre del Declarante:', signature_info.get('declarant_name', '_' * 40)],
            ['Fecha:', str(signature_info.get('declaration_date', '_' * 20))],
            ['Nombre Contador/Revisor:', signature_info.get('accountant_name', '_' * 40)],
            ['Tarjeta Profesional:', signature_info.get('professional_card_number', '_' * 20)],
        ]
        
        table = Table(sig_data, colWidths=[2*inch, 4.8*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(table)
        
        # Firma digital (imagen)
        signature_image = data.get('signature_data')
        if signature_image and data.get('is_signed'):
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph('Firma Digital:', self.styles['FieldLabel']))
            
            # Decodificar base64 si es necesario
            try:
                if signature_image.startswith('data:image'):
                    signature_image = signature_image.split(',')[1]
                img_data = base64.b64decode(signature_image)
                img_buffer = BytesIO(img_data)
                sig_img = Image(img_buffer, width=2*inch, height=1*inch)
                elements.append(sig_img)
            except (ValueError, TypeError, KeyError) as e:
                # Manejar errores de decodificación base64 o formato de imagen
                elements.append(Paragraph('[Firma digital incluida]', self.styles['Normal']))
            
            # Información de integridad
            elements.append(Spacer(1, 0.1*inch))
            integrity_text = f"""
            <font size="8">
            <b>Firmado el:</b> {data.get('signed_at', 'N/A')}<br/>
            <b>Hash de integridad:</b> {data.get('integrity_hash', 'N/A')[:32]}...
            </font>
            """
            elements.append(Paragraph(integrity_text, self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_footer(self) -> list:
        """Construye el pie de página."""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.1*inch))
        
        # Notas legales
        legal_notes = self.config.get('legal_notes', '')
        if legal_notes:
            elements.append(Paragraph(legal_notes, self.styles['Footer']))
        
        # Footer text
        footer_text = self.config.get('footer_text', '')
        if footer_text:
            elements.append(Paragraph(footer_text, self.styles['Footer']))
        
        # Timestamp de generación
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        elements.append(Paragraph(
            f'Documento generado el {timestamp}',
            self.styles['Footer']
        ))
        
        return elements
