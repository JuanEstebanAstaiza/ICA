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
            fontSize=10,
            textColor=colors.Color(r/255, g/255, b/255),
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=8,
            textColor=colors.Color(r/255, g/255, b/255),
            spaceBefore=2,
            spaceAfter=2
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldLabel',
            parent=self.styles['Normal'],
            fontSize=6,
            textColor=colors.grey
        ))
        
        self.styles.add(ParagraphStyle(
            name='FieldValue',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=5,
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
        # Usar márgenes reducidos para que el formulario quepa en una página
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.5*cm,
            leftMargin=0.5*cm,
            topMargin=0.5*cm,
            bottomMargin=0.5*cm
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
        elements.append(Spacer(1, 0.02*inch))
        
        # Metadatos
        elements.extend(self._build_metadata_section(declaration_data))
        
        # Sección A - Contribuyente
        elements.extend(self._build_taxpayer_section(declaration_data.get('taxpayer', {})))
        
        # Sección B - Base Gravable
        elements.extend(self._build_income_section(declaration_data.get('income_base', {})))
        
        # Sección C - Actividades (solo resumen en primera página)
        activities = declaration_data.get('activities', [])
        elements.extend(self._build_activities_section(activities))
        
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
        
        # Si hay actividades, agregar página de anexo con TODAS las actividades
        if len(activities) > 0:
            elements.append(PageBreak())
            elements.extend(self._build_activities_annex_section(activities))
        
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
            logo = Image(logo_path, width=1.5*inch, height=0.6*inch)
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
        
        elements.append(Spacer(1, 0.02*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 0.02*inch))
        
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
        
        # Layout compacto en 2 columnas
        metadata = [
            ['Año Gravable:', str(data.get('tax_year', '')), 'Tipo:', data.get('declaration_type', '').replace('_', ' ').title()],
            ['No. Formulario:', data.get('form_number', ''), 'No. Radicado:', data.get('filing_number', 'Pendiente')],
            ['Fecha:', filing_date or 'No presentada', 'Estado:', data.get('status', '').title()],
        ]
        
        table = Table(metadata, colWidths=[1.3*inch, 2.2*inch, 1.3*inch, 2.2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
        return elements
    
    def _build_taxpayer_section(self, taxpayer: dict) -> list:
        """Construye Sección A - Información del Contribuyente."""
        elements = []
        
        elements.append(Paragraph('Sección A – Información del Contribuyente', self.styles['SectionTitle']))
        
        data = [
            ['Tipo Doc:', taxpayer.get('document_type', ''),
             'Número:', taxpayer.get('document_number', ''),
             'DV:', taxpayer.get('verification_digit', '')],
            ['Razón Social:', taxpayer.get('legal_name', ''), '', '', '', ''],
            ['Dirección:', taxpayer.get('address', ''),
             'Municipio:', taxpayer.get('municipality', ''), '', ''],
            ['Depto:', taxpayer.get('department', ''),
             'Tel:', taxpayer.get('phone', ''),
             'Email:', taxpayer.get('email', '')],
        ]
        
        table = Table(data, colWidths=[0.9*inch, 1.8*inch, 0.9*inch, 1.5*inch, 0.6*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (4, 0), (4, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BACKGROUND', (4, 0), (4, -1), colors.Color(0.95, 0.95, 0.95)),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            # Span para razón social
            ('SPAN', (1, 1), (5, 1)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
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
            ['R', 'Concepto', 'Valor'],
            ['8', 'Total ingresos ordinarios y extraordinarios del período', fmt(r8)],
            ['9', 'Menos ingresos fuera del municipio', fmt(r9)],
            ['10', 'TOTAL INGRESOS EN EL MUNICIPIO (R8 - R9)', fmt(r10)],
            ['11', 'Menos devoluciones, rebajas y descuentos', fmt(r11)],
            ['12', 'Menos exportaciones y venta activos fijos', fmt(r12)],
            ['13', 'Menos actividades excluidas o no sujetas', fmt(r13)],
            ['14', 'Menos actividades exentas en el municipio', fmt(r14)],
            ['15', 'TOTAL INGRESOS GRAVABLES', fmt(r15)],
        ]
        
        table = Table(data, colWidths=[0.4*inch, 4.8*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            # Resaltar filas calculadas
            ('BACKGROUND', (0, 3), (-1, 3), colors.Color(0.9, 0.95, 0.9)),
            ('BACKGROUND', (0, 8), (-1, 8), colors.Color(0.9, 0.95, 0.9)),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTNAME', (0, 8), (-1, 8), 'Helvetica-Bold'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
        return elements
    
    def _build_activities_section(self, activities: list) -> list:
        """
        Construye Sección C - Actividades Gravadas (solo resumen en página principal).
        
        Las actividades individuales se muestran en el Anexo.
        
        Args:
            activities: Lista de actividades gravadas
        
        Returns:
            Lista de elementos para la sección de actividades (solo resumen)
        """
        elements = []
        
        elements.append(Paragraph('Sección C – Actividades Gravadas', self.styles['SectionTitle']))
        
        def fmt(value):
            return f"${value:,.0f}" if value else "$0"
        
        # Calcular el total de impuestos de TODAS las actividades
        total_tax = 0
        total_income = 0
        for act in activities:
            tax = act.get('income', 0) * act.get('tax_rate', 0) / 1000
            total_tax += tax
            total_income += act.get('income', 0)
        
        # Solo mostrar resumen con referencia al anexo
        data = [
            ['Concepto', 'Valor'],
            ['Número de actividades gravadas', str(len(activities))],
            ['Total ingresos por actividades', fmt(total_income)],
            ['TOTAL IMPUESTO POR ACTIVIDADES', fmt(total_tax)],
        ]
        
        # Calcular índice de fila del total (siempre es la fila después del header)
        total_row_index = len(data) - 1  # Última fila actual es el total
        
        # Si hay actividades, agregar referencia al anexo
        annex_reference_row = None
        if len(activities) > 0:
            data.append(['', f'Ver detalle de {len(activities)} actividad(es) en Anexo - Página 2'])
            annex_reference_row = len(data) - 1  # Última fila es la referencia al anexo
        
        table = Table(data, colWidths=[4.5*inch, 2*inch])
        
        # Configurar estilo
        style_commands = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            # Fila de total (usando índice calculado)
            ('FONTNAME', (0, total_row_index), (-1, total_row_index), 'Helvetica-Bold'),
            ('BACKGROUND', (0, total_row_index), (-1, total_row_index), colors.Color(0.9, 0.95, 0.9)),
            ('FONTSIZE', (0, total_row_index), (-1, total_row_index), 7),
        ]
        
        # Si hay referencia al anexo, estilizarla (usando índice calculado)
        if annex_reference_row is not None:
            style_commands.append(('FONTNAME', (1, annex_reference_row), (1, annex_reference_row), 'Helvetica-Oblique'))
            style_commands.append(('TEXTCOLOR', (1, annex_reference_row), (1, annex_reference_row), colors.Color(0.3, 0.3, 0.6)))
            style_commands.append(('FONTSIZE', (1, annex_reference_row), (1, annex_reference_row), 5))
        
        table.setStyle(TableStyle(style_commands))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
        return elements
    
    def _build_activities_annex_section(self, activities: list) -> list:
        """
        Construye la página de Anexo con TODAS las actividades.
        
        Args:
            activities: Lista completa de actividades gravadas
        
        Returns:
            Lista de elementos para la página de anexo
        """
        elements = []
        
        if not activities:
            return elements
        
        # Título del anexo
        elements.append(Paragraph('ANEXO – Detalle de Actividades Gravadas', self.styles['FormTitle']))
        elements.append(Spacer(1, 0.02*inch))
        
        # Subtítulo con información
        elements.append(Paragraph(
            f'Sección C – Detalle completo de actividades gravadas (Total: {len(activities)} actividad(es))',
            self.styles['SectionTitle']
        ))
        
        def fmt(value):
            return f"${value:,.0f}" if value else "$0"
        
        data = [['#', 'Código', 'Descripción', 'Ingresos', 'Tarifa‰', 'Impuesto']]
        
        total_tax = 0
        for i, act in enumerate(activities, start=1):
            tax = act.get('income', 0) * act.get('tax_rate', 0) / 1000
            total_tax += tax
            data.append([
                str(i),
                act.get('ciiu_code', ''),
                act.get('description', '')[:30],  # Truncar descripción
                fmt(act.get('income', 0)),
                f"{act.get('tax_rate', 0):.2f}",
                fmt(tax)
            ])
        
        # Fila de total de actividades
        data.append(['', '', 'TOTAL IMPUESTO POR ACTIVIDADES', '', '', fmt(total_tax)])
        
        table = Table(data, colWidths=[0.4*inch, 0.7*inch, 2.8*inch, 1.2*inch, 0.8*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            # Fila de total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.9, 0.95, 0.9)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
        # Nota informativa
        elements.append(Paragraph(
            '<i>Nota: Este anexo forma parte integral del formulario de declaración ICA. '
            'El total de impuestos por actividades se refleja en la primera página del formulario.</i>',
            self.styles['Footer']
        ))
        
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
        
        # Layout en 2 columnas para ahorrar espacio vertical
        data = [
            ['R', 'Concepto', 'Valor', 'R', 'Concepto', 'Valor'],
            ['20', 'Total impuesto ICA', fmt(r20), '27', 'Menos retenciones', fmt(r27)],
            ['21', 'Avisos y tableros', fmt(r21), '28', 'Menos autorretenciones', fmt(r28)],
            ['22', 'Unidades comerciales', fmt(r22), '29', 'Menos anticipo año ant.', fmt(r29)],
            ['23', 'Sobretasa bomberil', fmt(r23), '30', 'Anticipo año siguiente', fmt(r30)],
            ['24', 'Sobretasa seguridad', fmt(r24), '31', 'Sanciones', fmt(r31)],
            ['25', 'TOTAL A CARGO', fmt(r25), '32', 'Menos saldo favor ant.', fmt(r32)],
            ['26', 'Menos exenciones', fmt(r26), '33', 'SALDO A CARGO', fmt(r33)],
            ['', '', '', '34', 'SALDO A FAVOR', fmt(r34)],
        ]
        
        table = Table(data, colWidths=[0.3*inch, 1.6*inch, 0.9*inch, 0.3*inch, 1.6*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            # Resaltar filas importantes
            ('FONTNAME', (0, 6), (2, 6), 'Helvetica-Bold'),  # R25
            ('BACKGROUND', (0, 6), (2, 6), colors.Color(0.95, 0.95, 0.85)),
            ('FONTNAME', (3, 7), (5, 7), 'Helvetica-Bold'),  # R33
            ('BACKGROUND', (3, 7), (5, 7), colors.Color(0.95, 0.85, 0.85)),
            ('FONTNAME', (3, 8), (5, 8), 'Helvetica-Bold'),  # R34
            ('BACKGROUND', (3, 8), (5, 8), colors.Color(0.85, 0.95, 0.85)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
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
        
        # Layout compacto en 2 columnas
        data_table = [
            ['R', 'Concepto', 'Valor', 'R', 'Concepto', 'Valor'],
            ['35', 'Valor a pagar', fmt(r35), '38', 'TOTAL A PAGAR', fmt(r38)],
            ['36', 'Desc. pronto pago', fmt(r36), '39', f'Pago voluntario', fmt(r39)],
            ['37', 'Intereses mora', fmt(r37), '40', 'TOTAL CON VOL.', fmt(r40)],
        ]
        
        table = Table(data_table, colWidths=[0.3*inch, 1.5*inch, 0.9*inch, 0.3*inch, 1.5*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.4)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (5, 0), (5, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            # Resaltar TOTAL A PAGAR
            ('FONTNAME', (3, 1), (5, 1), 'Helvetica-Bold'),
            ('BACKGROUND', (3, 1), (5, 1), colors.Color(0.95, 0.95, 0.85)),
            # Resaltar TOTAL CON VOLUNTARIO
            ('FONTNAME', (3, 3), (5, 3), 'Helvetica-Bold'),
            ('BACKGROUND', (3, 3), (5, 3), colors.Color(0.85, 0.9, 0.95)),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.02*inch))
        
        return elements
    
    def _build_result_section(self, result: dict) -> list:
        """Construye sección de resumen final."""
        elements = []
        
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
            [f'SALDO {status}', fmt(amount)],
        ]
        
        table = Table(data, colWidths=[4.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BACKGROUND', (0, 0), (-1, 0), bg_color),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _build_signature_section(self, data: dict) -> list:
        """Construye Sección F - Firma del Declarante y Contador/Revisor Fiscal con imágenes de firmas."""
        elements = []
        
        # Título de la sección
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
        
        accountant_name = signature_info.get('accountant_name')
        requires_fiscal_reviewer = signature_info.get('requires_fiscal_reviewer', False)
        
        # Datos del declarante
        declarant_name = signature_info.get('declarant_name', '________')
        declarant_doc = signature_info.get('declarant_document', '________')
        declarant_signature_image = signature_info.get('declarant_signature_image', '')
        
        # Datos del contador/revisor
        accountant_doc = signature_info.get('accountant_document', '')
        accountant_card = signature_info.get('accountant_professional_card', '')
        accountant_signature_image = signature_info.get('accountant_signature_image', '')
        
        # Crear imagen de firma del declarante si existe
        declarant_signature_element = None
        if declarant_signature_image and declarant_signature_image.startswith('data:image'):
            try:
                # Extraer datos base64
                signature_base64 = declarant_signature_image.split(',')[1]
                signature_bytes = base64.b64decode(signature_base64)
                signature_buffer = BytesIO(signature_bytes)
                declarant_signature_element = Image(signature_buffer, width=1.5*inch, height=0.5*inch)
            except Exception as e:
                declarant_signature_element = Paragraph('_____________', self.styles['Normal'])
        else:
            declarant_signature_element = Paragraph('_____________', self.styles['Normal'])
        
        # Crear imagen de firma del contador si existe
        accountant_signature_element = None
        if accountant_name and accountant_signature_image and accountant_signature_image.startswith('data:image'):
            try:
                # Extraer datos base64
                signature_base64 = accountant_signature_image.split(',')[1]
                signature_bytes = base64.b64decode(signature_base64)
                signature_buffer = BytesIO(signature_bytes)
                accountant_signature_element = Image(signature_buffer, width=1.5*inch, height=0.5*inch)
            except Exception as e:
                accountant_signature_element = Paragraph('_____________', self.styles['Normal'])
        elif accountant_name:
            accountant_signature_element = Paragraph('_____________', self.styles['Normal'])
        
        if accountant_name:
            # Mostrar ambas firmas lado a lado
            title = "REVISOR FISCAL" if requires_fiscal_reviewer else "CONTADOR PÚBLICO"
            
            # Tabla con dos columnas para las firmas
            data_table = [
                ['FIRMA DEL DECLARANTE', '', title, ''],
                [declarant_signature_element, '', accountant_signature_element, ''],
                ['Nombre:', declarant_name, 'Nombre:', accountant_name],
                ['Documento:', declarant_doc, 'Documento:', accountant_doc],
                ['Fecha:', declaration_date or '________', 'T.P.:', accountant_card],
            ]
            table = Table(data_table, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 2.2*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
                ('SPAN', (0, 0), (1, 0)),  # Span título declarante
                ('SPAN', (2, 0), (3, 0)),  # Span título contador
                ('SPAN', (0, 1), (1, 1)),  # Span firma declarante
                ('SPAN', (2, 1), (3, 1)),  # Span firma contador
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 2), (2, -1), 'Helvetica-Bold'),
            ]))
        else:
            # Solo firma del declarante
            data_table = [
                ['FIRMA DEL DECLARANTE / REPRESENTANTE LEGAL'],
                [declarant_signature_element],
                ['Nombre:', declarant_name, '', ''],
                ['Documento:', declarant_doc, 'Fecha:', declaration_date or '________'],
            ]
            table = Table(data_table, colWidths=[0.8*inch, 2.2*inch, 0.8*inch, 2.2*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.95)),
                ('SPAN', (0, 0), (3, 0)),  # Span título
                ('SPAN', (0, 1), (3, 1)),  # Span firma
                ('SPAN', (1, 2), (3, 2)),  # Span nombre
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
                ('VALIGN', (0, 1), (-1, 1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 2), (2, -1), 'Helvetica-Bold'),
            ]))
        
        elements.append(table)
        
        # Información de integridad (si está firmado)
        if data.get('is_signed'):
            signed_at = signature_info.get('signed_at') or data.get('signed_at', 'N/A')
            integrity_hash = data.get('integrity_hash', '')
            if integrity_hash and len(integrity_hash) > 20:
                hash_display = integrity_hash[:20] + '...'
            else:
                hash_display = integrity_hash or 'N/A'
            
            elements.append(Spacer(1, 0.02*inch))
            integrity_text = f"<font size='4'>Firmado: {signed_at} | Hash: {hash_display}</font>"
            elements.append(Paragraph(integrity_text, self.styles['Footer']))
        
        return elements
    
    def _build_footer(self) -> list:
        """Construye el pie de página."""
        elements = []
        
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        
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
            f'Generado: {timestamp} (Hora Colombia)',
            self.styles['Footer']
        ))
        
        return elements
