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
from reportlab.pdfgen import canvas as pdf_canvas

from ..core.config import settings, get_pdf_path, get_colombia_time


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
        self.watermark_text = self.config.get('watermark_text', '')
    
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
            year = declaration_data.get('tax_year', get_colombia_time().year)
            municipality = declaration_data.get('municipality', {}).get('name', 'default')
            user_id = declaration_data.get('user_id', 0)
            
            base_path = get_pdf_path(year, municipality, user_id)
            os.makedirs(base_path, exist_ok=True)
            
            timestamp = get_colombia_time().strftime('%Y%m%d_%H%M%S')
            form_number = declaration_data.get('form_number', 'DRAFT')
            output_path = os.path.join(base_path, f"ICA_{form_number}_{timestamp}.pdf")
        
        # Crear documento con marca de agua
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        # Configurar marca de agua
        watermark = self.watermark_text
        
        def add_watermark(canvas, doc):
            """Agrega marca de agua diagonal en cada página."""
            if watermark:
                canvas.saveState()
                canvas.setFont('Helvetica-Bold', 50)
                canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.3))  # Gris claro semitransparente
                
                # Posicionar en el centro de la página
                page_width, page_height = letter
                canvas.translate(page_width / 2, page_height / 2)
                canvas.rotate(45)  # Rotación diagonal
                
                # Dibujar texto centrado
                canvas.drawCentredString(0, 0, watermark)
                canvas.restoreState()
        
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
        
        # Sección E - Pago
        elements.extend(self._build_discounts_section(declaration_data.get('payment', {})))
        
        # Resumen/Resultado
        elements.extend(self._build_result_section(declaration_data.get('result', {})))
        
        # Sección G - Firma
        elements.extend(self._build_signature_section(declaration_data))
        
        # Footer con notas legales
        elements.extend(self._build_footer())
        
        # Generar PDF con marca de agua
        if watermark:
            doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
        else:
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
        
        # Formatear fecha de presentación si existe
        filing_date = data.get('filing_date', '')
        if filing_date:
            try:
                from datetime import datetime
                if isinstance(filing_date, str):
                    dt = datetime.fromisoformat(filing_date.replace('Z', '+00:00'))
                    filing_date = dt.strftime('%d/%m/%Y %H:%M')
            except:
                pass
        
        metadata = [
            ['Año Gravable:', str(data.get('tax_year', ''))],
            ['Tipo de Declaración:', data.get('declaration_type', '').replace('_', ' ').title()],
            ['Número de Formulario:', data.get('form_number', '')],
            ['Número de Radicado:', data.get('filing_number', 'Pendiente')],
            ['Fecha de Presentación:', filing_date or 'No presentada'],
            ['Estado:', data.get('status', '').title()],
        ]
        
        table = Table(metadata, colWidths=[2.5*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
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
        """Construye Sección B - Base Gravable (Renglones 8-15)."""
        elements = []
        
        elements.append(Paragraph('Sección B – Base Gravable', self.styles['SectionTitle']))
        
        # Formatear valores monetarios
        def fmt(value):
            v = value or 0
            return f"${v:,.0f}"
        
        # Leer datos (compatible con nuevo y viejo formato)
        r8 = income.get('row_8', income.get('row_8_ordinary_income', 0)) or 0
        r9 = income.get('row_9', income.get('row_9_extraordinary_income', 0)) or 0
        r10 = income.get('row_10', r8 - r9) or 0
        r11 = income.get('row_11', income.get('row_11_returns', 0)) or 0
        r12 = income.get('row_12', income.get('row_12_exports', 0)) or 0
        r13 = income.get('row_13', income.get('row_13_fixed_assets_sales', 0)) or 0
        r14 = income.get('row_14', income.get('row_14_excluded_income', 0)) or 0
        r15 = income.get('row_15', 0) or 0
        if r15 == 0:
            r15 = r10 - (r11 + r12 + r13 + r14)
        
        data = [
            ['Renglón', 'Concepto', 'Valor'],
            ['8', 'Total ingresos ordinarios y extraordinarios del período en todo el país', fmt(r8)],
            ['9', 'Menos ingresos fuera del municipio', fmt(r9)],
            ['10', 'TOTAL INGRESOS EN EL MUNICIPIO (R8 - R9)', fmt(r10)],
            ['11', 'Menos ingresos por devoluciones, rebajas y descuentos', fmt(r11)],
            ['12', 'Menos ingresos por exportaciones y venta de activos fijos', fmt(r12)],
            ['13', 'Menos ingresos por actividades excluidas o no sujetas', fmt(r13)],
            ['14', 'Menos ingresos por actividades exentas en el municipio', fmt(r14)],
            ['15', 'TOTAL INGRESOS GRAVABLES (R10 - R11 - R12 - R13 - R14)', fmt(r15)],
        ]
        
        table = Table(data, colWidths=[0.8*inch, 4.2*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            # Resaltar filas calculadas
            ('BACKGROUND', (0, 3), (-1, 3), colors.Color(0.9, 0.95, 0.9)),
            ('BACKGROUND', (0, 8), (-1, 8), colors.Color(0.9, 0.95, 0.9)),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTNAME', (0, 8), (-1, 8), 'Helvetica-Bold'),
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
        """Construye Sección D - Liquidación del Impuesto (Renglones 20-34)."""
        elements = []
        
        elements.append(Paragraph('Sección D – Liquidación del Impuesto', self.styles['SectionTitle']))
        
        def fmt(value):
            v = value or 0
            return f"${v:,.0f}"
        
        # Leer datos con valores por defecto
        r20 = settlement.get('row_20', settlement.get('row_30_ica_tax', 0)) or 0
        r21 = settlement.get('row_21', settlement.get('row_31_signs_boards', 0)) or 0
        r22 = settlement.get('row_22', 0) or 0
        r23 = settlement.get('row_23', settlement.get('row_32_surcharge', 0)) or 0
        r24 = settlement.get('row_24', 0) or 0
        r25 = settlement.get('row_25', r20 + r21 + r22 + r23 + r24) or 0
        r26 = settlement.get('row_26', 0) or 0
        r27 = settlement.get('row_27', 0) or 0
        r28 = settlement.get('row_28', 0) or 0
        r29 = settlement.get('row_29', 0) or 0
        r30 = settlement.get('row_30', 0) or 0
        r31 = settlement.get('row_31', 0) or 0
        r32 = settlement.get('row_32', 0) or 0
        r33 = settlement.get('row_33', 0) or 0
        r34 = settlement.get('row_34', 0) or 0
        
        data = [
            ['Renglón', 'Concepto', 'Valor'],
            ['20', 'Total impuesto de industria y comercio (R17 + R19)', fmt(r20)],
            ['21', 'Impuesto de avisos y tableros', fmt(r21)],
            ['22', 'Pago unidades comerciales adicionales sector financiero', fmt(r22)],
            ['23', 'Sobretasa bomberil', fmt(r23)],
            ['24', 'Sobretasa de seguridad', fmt(r24)],
            ['25', 'TOTAL IMPUESTO A CARGO (R20+R21+R22+R23+R24)', fmt(r25)],
            ['26', 'Menos exenciones o exoneraciones', fmt(r26)],
            ['27', 'Menos retenciones practicadas', fmt(r27)],
            ['28', 'Menos autorretenciones', fmt(r28)],
            ['29', 'Menos anticipo liquidado año anterior', fmt(r29)],
            ['30', 'Anticipo del año siguiente', fmt(r30)],
            ['31', 'Sanciones', fmt(r31)],
            ['32', 'Menos saldo a favor período anterior', fmt(r32)],
            ['33', 'TOTAL SALDO A CARGO', fmt(r33)],
            ['34', 'TOTAL SALDO A FAVOR', fmt(r34)],
        ]
        
        table = Table(data, colWidths=[0.6*inch, 4.4*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            # Resaltar filas importantes
            ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),  # R25
            ('BACKGROUND', (0, 6), (-1, 6), colors.Color(0.95, 0.95, 0.85)),
            ('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold'),  # R33
            ('BACKGROUND', (0, 14), (-1, 14), colors.Color(0.95, 0.85, 0.85)),  # Rojo claro
            ('FONTNAME', (0, 15), (-1, 15), 'Helvetica-Bold'),  # R34
            ('BACKGROUND', (0, 15), (-1, 15), colors.Color(0.85, 0.95, 0.85)),  # Verde claro
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_discounts_section(self, data: dict) -> list:
        """Construye Sección E - Pago (Renglones 35-40)."""
        elements = []
        
        elements.append(Paragraph('Sección E – Pago', self.styles['SectionTitle']))
        
        def fmt(value):
            v = value or 0
            return f"${v:,.0f}"
        
        # Obtener datos de la sección payment
        payment = data if isinstance(data, dict) else {}
        
        r35 = payment.get('row_35', 0) or 0
        r36 = payment.get('row_36', 0) or 0
        r37 = payment.get('row_37', 0) or 0
        r38 = payment.get('row_38', r35 - r36 + r37) or 0
        r39 = payment.get('row_39', 0) or 0
        r39_dest = payment.get('row_39_destination', '')
        r40 = payment.get('row_40', r38 + r39) or 0
        
        data_table = [
            ['Renglón', 'Concepto', 'Valor'],
            ['35', 'Valor a pagar (desde saldo a cargo R33)', fmt(r35)],
            ['36', 'Descuento por pronto pago', fmt(r36)],
            ['37', 'Intereses de mora', fmt(r37)],
            ['38', 'TOTAL A PAGAR (R35 - R36 + R37)', fmt(r38)],
            ['39', f'Pago voluntario{" - " + r39_dest if r39_dest else ""}', fmt(r39)],
            ['40', 'TOTAL A PAGAR CON PAGO VOLUNTARIO (R38 + R39)', fmt(r40)],
        ]
        
        table = Table(data_table, colWidths=[0.6*inch, 4.4*inch, 1.8*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            # Resaltar filas importantes
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),  # R38
            ('BACKGROUND', (0, 4), (-1, 4), colors.Color(0.95, 0.95, 0.85)),
            ('FONTNAME', (0, 6), (-1, 6), 'Helvetica-Bold'),  # R40
            ('BACKGROUND', (0, 6), (-1, 6), colors.Color(0.85, 0.9, 0.95)),  # Azul claro
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_result_section(self, result: dict) -> list:
        """Construye sección de resumen final."""
        elements = []
        
        elements.append(Paragraph('Resumen de la Declaración', self.styles['SectionTitle']))
        
        def fmt(value):
            v = value or 0
            return f"${v:,.0f}"
        
        amount_to_pay = result.get('amount_to_pay', 0) or 0
        balance_in_favor = result.get('balance_in_favor', 0) or 0
        
        # Solo mostrar el que tenga valor
        if amount_to_pay > 0:
            status = "A CARGO"
            amount = amount_to_pay
            bg_color = colors.Color(0.95, 0.85, 0.85)  # Rojo claro
        elif balance_in_favor > 0:
            status = "A FAVOR"
            amount = balance_in_favor
            bg_color = colors.Color(0.85, 0.95, 0.85)  # Verde claro
        else:
            status = "EN CEROS"
            amount = 0
            bg_color = colors.Color(0.95, 0.95, 0.95)  # Gris claro
        
        data = [
            ['Estado de la Declaración', 'Monto'],
            [f'SALDO {status}', fmt(amount)],
        ]
        
        table = Table(data, colWidths=[4.8*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, 1), bg_color),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_signature_section(self, data: dict) -> list:
        """Construye Sección F - Firma del Declarante y Contador/Revisor Fiscal."""
        elements = []
        
        elements.append(Paragraph('Sección F – Firmas', self.styles['SectionTitle']))
        
        # Datos de firma - buscar en signature_info primero, luego en data directamente
        signature_info = data.get('signature_info', {})
        
        # Formatear fecha de firma
        declaration_date = signature_info.get('declaration_date', '')
        if declaration_date:
            try:
                from datetime import datetime
                if isinstance(declaration_date, str):
                    dt = datetime.fromisoformat(declaration_date)
                    declaration_date = dt.strftime('%d/%m/%Y')
            except:
                pass
        
        # FIRMA DEL DECLARANTE / REPRESENTANTE LEGAL
        elements.append(Paragraph('<b>FIRMA DEL DECLARANTE / REPRESENTANTE LEGAL</b>', self.styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        
        declarant_data = [
            ['Nombre Completo:', signature_info.get('declarant_name', '___________________________________')],
            ['Documento:', signature_info.get('declarant_document', '___________________________________')],
            ['Fecha de Firma:', declaration_date or '___________________________________'],
        ]
        
        table1 = Table(declarant_data, colWidths=[1.8*inch, 5*inch])
        table1.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        elements.append(table1)
        elements.append(Spacer(1, 0.2*inch))
        
        # Firma digital del declarante (imagen)
        # Buscar en signature_info.declarant_signature_image primero, luego en data.signature_data
        declarant_signature_image = signature_info.get('declarant_signature_image') or data.get('signature_data')
        if declarant_signature_image and data.get('is_signed'):
            elements.append(Paragraph('Firma Digital del Declarante:', self.styles['FieldLabel']))
            
            # Decodificar base64 si es necesario
            try:
                if declarant_signature_image.startswith('data:image'):
                    declarant_signature_image = declarant_signature_image.split(',')[1]
                img_data = base64.b64decode(declarant_signature_image)
                img_buffer = BytesIO(img_data)
                sig_img = Image(img_buffer, width=2*inch, height=1*inch)
                elements.append(sig_img)
            except (ValueError, TypeError, KeyError) as e:
                # Manejar errores de decodificación base64 o formato de imagen
                elements.append(Paragraph('[Firma digital incluida]', self.styles['Normal']))
            
            elements.append(Spacer(1, 0.2*inch))
        
        # FIRMA DEL CONTADOR / REVISOR FISCAL (solo si aplica)
        # Se muestra esta sección si hay datos del contador/revisor (accountant_name)
        requires_fiscal_reviewer = signature_info.get('requires_fiscal_reviewer', False)
        accountant_name = signature_info.get('accountant_name')
        
        if accountant_name:
            # Determinar si es contador público o revisor fiscal basado en requires_fiscal_reviewer
            title = "FIRMA DEL REVISOR FISCAL" if requires_fiscal_reviewer else "FIRMA DEL CONTADOR PÚBLICO"
            elements.append(Paragraph(f'<b>{title}</b>', self.styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            
            accountant_data = [
                ['Nombre:', signature_info.get('accountant_name', '___________________________________')],
                ['Documento:', signature_info.get('accountant_document', '___________________________________')],
                ['Tarjeta Profesional:', signature_info.get('accountant_professional_card', '___________________________________')],
            ]
            
            table2 = Table(accountant_data, colWidths=[1.8*inch, 5*inch])
            table2.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]))
            elements.append(table2)
            elements.append(Spacer(1, 0.1*inch))
            
            # Firma digital del contador/revisor (imagen)
            accountant_signature_image = signature_info.get('accountant_signature_image')
            if accountant_signature_image:
                elements.append(Paragraph(f'Firma Digital del {title.split(" DEL ")[1]}:', self.styles['FieldLabel']))
                
                try:
                    if accountant_signature_image.startswith('data:image'):
                        accountant_signature_image = accountant_signature_image.split(',')[1]
                    img_data = base64.b64decode(accountant_signature_image)
                    img_buffer = BytesIO(img_data)
                    sig_img = Image(img_buffer, width=2*inch, height=1*inch)
                    elements.append(sig_img)
                except (ValueError, TypeError, KeyError) as e:
                    elements.append(Paragraph('[Firma digital incluida]', self.styles['Normal']))
            
            elements.append(Spacer(1, 0.2*inch))
        
        # Información de integridad (si está firmado)
        if data.get('is_signed'):
            elements.append(Spacer(1, 0.1*inch))
            signed_at = signature_info.get('signed_at') or data.get('signed_at', 'N/A')
            integrity_hash = data.get('integrity_hash', '')
            if integrity_hash and integrity_hash != 'N/A' and len(integrity_hash) > 32:
                hash_display = integrity_hash[:32] + '...'
            else:
                hash_display = integrity_hash or 'N/A'
            integrity_text = f"""
            <font size="8">
            <b>Firmado el:</b> {signed_at}<br/>
            <b>Hash de integridad:</b> {hash_display}
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
        
        # Timestamp de generación (usando hora de Colombia)
        timestamp = get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
        elements.append(Paragraph(
            f'Documento generado el {timestamp} (Hora Colombia)',
            self.styles['Footer']
        ))
        
        return elements
