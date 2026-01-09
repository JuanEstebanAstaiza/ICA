"""
Servicio de generación de PDF.
Genera PDF institucional basado en el formulario ICA.
Formulario condensado en una única tabla con celdas ajustables.
"""
import os
from datetime import datetime
from typing import Optional
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from ..core.config import settings, get_pdf_path, get_colombia_time


# ===================== CONSTANTES DE DISEÑO =====================
PAGE_WIDTH = 7.5 * inch  # Letter - márgenes

# Colores institucionales
COLOR_HEADER = colors.Color(0.12, 0.16, 0.35)  # Azul oscuro
COLOR_SECTION = colors.Color(0.2, 0.25, 0.45)  # Azul sección
COLOR_SUBHEADER = colors.Color(0.85, 0.88, 0.95)  # Azul claro
COLOR_GREEN = colors.Color(0.88, 0.95, 0.88)
COLOR_RED = colors.Color(0.98, 0.88, 0.88)
COLOR_YELLOW = colors.Color(0.98, 0.96, 0.85)
COLOR_GRID = colors.Color(0.7, 0.7, 0.7)

# Tamaños de fuente
FONT_TITLE = 10
FONT_SECTION = 7
FONT_NORMAL = 6
FONT_SMALL = 5

# Padding
PAD = 2


class PDFGenerator:
    """Generador de PDF para declaraciones ICA - Formulario unificado."""
    
    def __init__(self, white_label_config: dict = None):
        self.config = white_label_config or {}
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        self.watermark_text = self.config.get('watermark_text', '')
        
        primary_hex = self.config.get('primary_color', '#1E2959')
        r, g, b = self._hex_to_rgb(primary_hex)
        self.primary_color = colors.Color(r/255, g/255, b/255)
    
    def _setup_styles(self):
        primary_hex = self.config.get('primary_color', '#1E2959')
        r, g, b = self._hex_to_rgb(primary_hex)
        primary = colors.Color(r/255, g/255, b/255)
        
        self.styles.add(ParagraphStyle(
            name='FormTitle',
            fontName='Helvetica-Bold',
            fontSize=FONT_TITLE,
            textColor=primary,
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='MuniHeader',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=primary,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            fontName='Helvetica',
            fontSize=5,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
        
        # Estilos para celdas con wrap
        self.styles.add(ParagraphStyle(
            name='CellNormal',
            fontName='Helvetica',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_LEFT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellBold',
            fontName='Helvetica-Bold',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_LEFT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellRight',
            fontName='Helvetica',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_RIGHT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellRightBold',
            fontName='Helvetica-Bold',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_RIGHT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellCenter',
            fontName='Helvetica',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_CENTER,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellCenterBold',
            fontName='Helvetica-Bold',
            fontSize=FONT_NORMAL,
            leading=FONT_NORMAL + 2,
            alignment=TA_CENTER,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellSmall',
            fontName='Helvetica',
            fontSize=FONT_SMALL,
            leading=FONT_SMALL + 2,
            alignment=TA_LEFT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellWhite',
            fontName='Helvetica-Bold',
            fontSize=FONT_SECTION,
            leading=FONT_SECTION + 2,
            textColor=colors.white,
            alignment=TA_LEFT,
            wordWrap='CJK'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CellLabel',
            fontName='Helvetica-Bold',
            fontSize=FONT_SMALL,
            leading=FONT_SMALL + 2,
            alignment=TA_LEFT,
            wordWrap='CJK'
        ))
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _fmt(self, value) -> str:
        v = value or 0
        return f"${v:,.0f}"
    
    def _p(self, text, style='CellNormal'):
        """Crear Paragraph con estilo."""
        return Paragraph(str(text) if text else '', self.styles[style])
    
    def _p_right(self, text, bold=False):
        """Crear Paragraph alineado a la derecha."""
        style = 'CellRightBold' if bold else 'CellRight'
        return Paragraph(str(text) if text else '', self.styles[style])
    
    def _p_bold(self, text):
        """Crear Paragraph en negrita."""
        return Paragraph(str(text) if text else '', self.styles['CellBold'])
    
    def _p_center(self, text, bold=False):
        """Crear Paragraph centrado."""
        style = 'CellCenterBold' if bold else 'CellCenter'
        return Paragraph(str(text) if text else '', self.styles[style])
    
    def _p_label(self, text):
        """Crear Paragraph para etiqueta pequeña."""
        return Paragraph(str(text) if text else '', self.styles['CellLabel'])
    
    def _p_small(self, text):
        """Crear Paragraph pequeño."""
        return Paragraph(str(text) if text else '', self.styles['CellSmall'])
    
    def _p_section(self, text):
        """Crear Paragraph para título de sección."""
        return Paragraph(str(text) if text else '', self.styles['CellWhite'])
    
    def generate_declaration_pdf(self, declaration_data: dict, output_path: Optional[str] = None) -> str:
        """Genera el PDF de una declaración ICA en una sola tabla."""
        if not output_path:
            year = declaration_data.get('tax_year', get_colombia_time().year)
            municipality = declaration_data.get('municipality', {}).get('name', 'default')
            user_id = declaration_data.get('user_id', 0)
            
            base_path = get_pdf_path(year, municipality, user_id)
            os.makedirs(base_path, exist_ok=True)
            
            timestamp = get_colombia_time().strftime('%Y%m%d_%H%M%S')
            form_number = declaration_data.get('form_number', 'DRAFT')
            output_path = os.path.join(base_path, f"ICA_{form_number}_{timestamp}.pdf")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.4*inch,
            leftMargin=0.4*inch,
            topMargin=0.3*inch,
            bottomMargin=0.3*inch
        )
        
        watermark = self.watermark_text
        
        def add_watermark(canvas, doc):
            if watermark:
                canvas.saveState()
                canvas.setFont('Helvetica-Bold', 45)
                canvas.setFillColor(colors.Color(0.85, 0.85, 0.85, alpha=0.25))
                page_width, page_height = letter
                canvas.translate(page_width / 2, page_height / 2)
                canvas.rotate(45)
                canvas.drawCentredString(0, 0, watermark)
                canvas.restoreState()
        
        elements = []
        
        # Header
        elements.extend(self._build_header(declaration_data))
        
        # Título
        form_title = self.config.get('form_title', 'Formulario Único Nacional de Declaración y Pago ICA')
        elements.append(Paragraph(form_title, self.styles['FormTitle']))
        
        # Tabla principal unificada
        elements.append(self._build_unified_table(declaration_data))
        
        # Footer
        elements.extend(self._build_footer())
        
        # Anexo si hay actividades
        activities = declaration_data.get('activities', [])
        if len(activities) > 0:
            elements.append(PageBreak())
            elements.extend(self._build_activities_annex(activities))
        
        if watermark:
            doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)
        else:
            doc.build(elements)
        
        return output_path
    
    def _build_header(self, data: dict) -> list:
        elements = []
        
        logo_path = self.config.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1*inch, height=0.4*inch)
                elements.append(logo)
            except:
                pass
        
        municipality = data.get('municipality', {})
        if municipality:
            muni_text = f"<b>{municipality.get('name', '')}</b> - {municipality.get('department', '')}"
            elements.append(Paragraph(muni_text, self.styles['MuniHeader']))
        
        elements.append(HRFlowable(width="100%", thickness=1, color=self.primary_color))
        elements.append(Spacer(1, 2))
        
        return elements
    
    def _build_unified_table(self, data: dict) -> Table:
        """Construye una tabla única con todo el formulario usando Paragraphs."""
        
        # Obtener todos los datos
        taxpayer = data.get('taxpayer', {})
        income = data.get('income_base', {})
        activities = data.get('activities', [])
        settlement = data.get('settlement', {})
        payment = data.get('payment', {})
        result = data.get('result', {})
        signature_info = data.get('signature_info', {})
        
        # Formatear fecha de presentación
        filing_date = data.get('filing_date', '')
        if filing_date:
            try:
                if isinstance(filing_date, str):
                    dt = datetime.fromisoformat(filing_date.replace('Z', '+00:00'))
                    filing_date = dt.strftime('%d/%m/%Y %H:%M')
            except:
                pass
        
        # Calcular valores de income
        r8 = income.get('row_8', income.get('row_8_ordinary_income', 0)) or 0
        r9 = income.get('row_9', income.get('row_9_extraordinary_income', 0)) or 0
        r10 = r8 - r9
        r11 = income.get('row_11', income.get('row_11_returns', 0)) or 0
        r12 = income.get('row_12', income.get('row_12_exports', 0)) or 0
        r13 = income.get('row_13', income.get('row_13_fixed_assets_sales', 0)) or 0
        r14 = income.get('row_14', income.get('row_14_excluded_income', 0)) or 0
        r15 = income.get('row_15', 0) or 0
        if r15 == 0:
            r15 = r10 - (r11 + r12 + r13 + r14)
        
        # Calcular actividades
        total_activities_tax = 0
        total_activities_income = 0
        for act in activities:
            inc = act.get('income', 0) or 0
            rate = act.get('tax_rate', 0) or 0
            total_activities_income += inc
            total_activities_tax += inc * rate / 100  # Porcentaje
        
        # Settlement values
        r20 = settlement.get('row_20', total_activities_tax) or 0
        r21 = settlement.get('row_21', 0) or 0
        r22 = settlement.get('row_22', 0) or 0
        r23 = settlement.get('row_23', 0) or 0
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
        
        # Payment values
        r35 = payment.get('row_35', 0) or 0
        r36 = payment.get('row_36', 0) or 0
        r37 = payment.get('row_37', 0) or 0
        r38 = payment.get('row_38', r35 - r36 + r37) or 0
        r39 = payment.get('row_39', 0) or 0
        r40 = payment.get('row_40', r38 + r39) or 0
        
        # Result
        amount_to_pay = result.get('amount_to_pay', 0) or 0
        balance_in_favor = result.get('balance_in_favor', 0) or 0
        
        # Signature data
        declarant_name = signature_info.get('declarant_name', '________________')
        declarant_doc = signature_info.get('declarant_document', '________________')
        accountant_name = signature_info.get('accountant_name', '')
        accountant_card = signature_info.get('accountant_professional_card', '')
        requires_fiscal = signature_info.get('requires_fiscal_reviewer', False)
        
        declaration_date = signature_info.get('declaration_date', '')
        if declaration_date:
            try:
                if isinstance(declaration_date, str):
                    dt = datetime.fromisoformat(declaration_date)
                    declaration_date = dt.strftime('%d/%m/%Y')
            except:
                pass
        
        # ===================== CONSTRUIR FILAS DE LA TABLA =====================
        # Definir anchos de 6 columnas para layout flexible
        # Total: ~7.2 inches
        c1, c2, c3, c4, c5, c6 = 0.5*inch, 1.9*inch, 0.75*inch, 0.5*inch, 1.7*inch, 0.85*inch
        col_widths = [c1, c2, c3, c4, c5, c6]
        
        rows = []
        styles = []
        row_idx = 0
        
        # ─────────── METADATOS ───────────
        rows.append([
            self._p_label('Año:'), self._p(data.get('tax_year', '')),
            self._p_label('Tipo:'), self._p(data.get('declaration_type', '').replace('_', ' ').title()),
            self._p_label('Estado:'), self._p(data.get('status', '').title())
        ])
        styles.extend([
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (4, row_idx), (4, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        # Número de formulario - truncar si es muy largo
        form_number = data.get('form_number', '')
        filing_number = data.get('filing_number', 'Pendiente')
        
        rows.append([
            self._p_label('Form:'), self._p_small(form_number),
            self._p_label('Radicado:'), self._p_small(filing_number),
            self._p_label('Fecha:'), self._p_small(filing_date or 'No presentada')
        ])
        styles.extend([
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (4, row_idx), (4, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        # ─────────── SECCIÓN A - CONTRIBUYENTE ───────────
        rows.append([self._p_section('Sección A – Información del Contribuyente'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        rows.append([
            self._p_label('Tipo Doc:'), self._p(taxpayer.get('document_type', '')),
            self._p_label('Número:'), self._p(taxpayer.get('document_number', '')),
            self._p_label('DV:'), self._p(taxpayer.get('verification_digit', ''))
        ])
        styles.extend([
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (4, row_idx), (4, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        rows.append([self._p_label('Razón Social:'), self._p(taxpayer.get('legal_name', '')), '', '', '', ''])
        styles.extend([
            ('SPAN', (1, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        rows.append([
            self._p_label('Dirección:'), self._p(taxpayer.get('address', '')),
            self._p_label('Municipio:'), self._p(taxpayer.get('municipality', '')), '', ''
        ])
        styles.extend([
            ('SPAN', (1, row_idx), (1, row_idx)),
            ('SPAN', (3, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        rows.append([
            self._p_label('Depto:'), self._p(taxpayer.get('department', '')),
            self._p_label('Tel:'), self._p(taxpayer.get('phone', '')),
            self._p_label('Email:'), self._p_small(taxpayer.get('email', ''))
        ])
        styles.extend([
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (4, row_idx), (4, row_idx), COLOR_SUBHEADER),
        ])
        row_idx += 1
        
        # ─────────── SECCIÓN B - BASE GRAVABLE ───────────
        rows.append([self._p_section('Sección B – Base Gravable'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        income_rows = [
            ('8', 'Total ingresos ordinarios y extraordinarios', self._fmt(r8), False),
            ('9', 'Menos ingresos fuera del municipio', self._fmt(r9), False),
            ('10', 'TOTAL INGRESOS EN EL MUNICIPIO (R8 - R9)', self._fmt(r10), True),
            ('11', 'Menos devoluciones, rebajas y descuentos', self._fmt(r11), False),
            ('12', 'Menos exportaciones y venta activos fijos', self._fmt(r12), False),
            ('13', 'Menos actividades excluidas o no sujetas', self._fmt(r13), False),
            ('14', 'Menos actividades exentas en el municipio', self._fmt(r14), False),
            ('15', 'TOTAL INGRESOS GRAVABLES', self._fmt(r15), True),
        ]
        
        for rnum, concept, value, is_total in income_rows:
            if is_total:
                rows.append([self._p_bold(rnum), self._p_bold(concept), '', '', '', self._p_right(value, bold=True)])
            else:
                rows.append([self._p(rnum), self._p(concept), '', '', '', self._p_right(value)])
            styles.append(('SPAN', (1, row_idx), (4, row_idx)))
            if is_total:
                styles.append(('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_GREEN))
            row_idx += 1
        
        # ─────────── SECCIÓN C - ACTIVIDADES ───────────
        rows.append([self._p_section('Sección C – Actividades Gravadas'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        rows.append([
            self._p_label('Actividades:'), self._p(str(len(activities))),
            self._p_label('Ingresos:'), self._p_right(self._fmt(total_activities_income)),
            self._p_label('Impuesto:'), self._p_right(self._fmt(total_activities_tax), bold=True)
        ])
        styles.extend([
            ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
            ('BACKGROUND', (4, row_idx), (5, row_idx), COLOR_GREEN),
        ])
        row_idx += 1
        
        # ─────────── SECCIÓN D - LIQUIDACIÓN ───────────
        rows.append([self._p_section('Sección D – Liquidación del Impuesto'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        # Layout 2 columnas para liquidación
        settlement_pairs = [
            ('20', 'Total impuesto ICA', r20, '27', 'Menos retenciones', r27),
            ('21', 'Avisos y tableros', r21, '28', 'Menos autorretenciones', r28),
            ('22', 'Unidades comerciales', r22, '29', 'Menos anticipo año ant.', r29),
            ('23', 'Sobretasa bomberil', r23, '30', 'Anticipo año siguiente', r30),
            ('24', 'Sobretasa seguridad', r24, '31', 'Sanciones', r31),
            ('25', 'TOTAL A CARGO', r25, '32', 'Menos saldo favor ant.', r32),
            ('26', 'Menos exenciones', r26, '33', 'SALDO A CARGO', r33),
            ('', '', '', '34', 'SALDO A FAVOR', r34),
        ]
        
        for r1, c1_text, v1, r2, c2_text, v2 in settlement_pairs:
            is_25 = r1 == '25'
            is_33 = r2 == '33'
            is_34 = r2 == '34'
            
            row_data = [
                self._p_bold(r1) if is_25 else self._p(r1),
                self._p_bold(c1_text) if is_25 else self._p(c1_text),
                self._p_right(self._fmt(v1), bold=is_25) if v1 or r1 else self._p(''),
                self._p_bold(r2) if (is_33 or is_34) else self._p(r2),
                self._p_bold(c2_text) if (is_33 or is_34) else self._p(c2_text),
                self._p_right(self._fmt(v2), bold=(is_33 or is_34))
            ]
            rows.append(row_data)
            
            if is_25:
                styles.append(('BACKGROUND', (0, row_idx), (2, row_idx), COLOR_YELLOW))
            if is_33:
                styles.append(('BACKGROUND', (3, row_idx), (5, row_idx), COLOR_RED))
            if is_34:
                styles.append(('BACKGROUND', (3, row_idx), (5, row_idx), COLOR_GREEN))
            row_idx += 1
        
        # ─────────── SECCIÓN E - PAGO ───────────
        rows.append([self._p_section('Sección E – Pago'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        payment_pairs = [
            ('35', 'Valor a pagar', r35, '38', 'TOTAL A PAGAR', r38, False, True),
            ('36', 'Desc. pronto pago', r36, '39', 'Pago voluntario', r39, False, False),
            ('37', 'Intereses mora', r37, '40', 'TOTAL CON VOLUNTARIO', r40, False, True),
        ]
        
        for r1, c1_text, v1, r2, c2_text, v2, bold1, bold2 in payment_pairs:
            row_data = [
                self._p(r1),
                self._p(c1_text),
                self._p_right(self._fmt(v1)),
                self._p_bold(r2) if bold2 else self._p(r2),
                self._p_bold(c2_text) if bold2 else self._p(c2_text),
                self._p_right(self._fmt(v2), bold=bold2)
            ]
            rows.append(row_data)
            
            if r2 == '38':
                styles.append(('BACKGROUND', (3, row_idx), (5, row_idx), COLOR_YELLOW))
            if r2 == '40':
                styles.append(('BACKGROUND', (3, row_idx), (5, row_idx), COLOR_SUBHEADER))
            row_idx += 1
        
        # ─────────── RESUMEN ───────────
        if amount_to_pay > 0:
            status_text = "SALDO A CARGO"
            status_value = self._fmt(amount_to_pay)
            status_color = COLOR_RED
        elif balance_in_favor > 0:
            status_text = "SALDO A FAVOR"
            status_value = self._fmt(balance_in_favor)
            status_color = COLOR_GREEN
        else:
            status_text = "SALDO EN CEROS"
            status_value = "$0"
            status_color = COLOR_SUBHEADER
        
        rows.append([self._p_bold(status_text), '', '', '', '', self._p_right(status_value, bold=True)])
        styles.extend([
            ('SPAN', (0, row_idx), (4, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), status_color),
        ])
        row_idx += 1
        
        # ─────────── SECCIÓN F - FIRMAS ───────────
        rows.append([self._p_section('Sección F – Firmas'), '', '', '', '', ''])
        styles.extend([
            ('SPAN', (0, row_idx), (5, row_idx)),
            ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SECTION),
        ])
        row_idx += 1
        
        # Firmas
        title_acc = "REVISOR FISCAL" if requires_fiscal else "CONTADOR" if accountant_name else ""
        
        # Crear imágenes de firma
        declarant_sig = signature_info.get('declarant_signature_image', '')
        accountant_sig = signature_info.get('accountant_signature_image', '')
        
        declarant_sig_el = self._create_signature_image(declarant_sig)
        accountant_sig_el = self._create_signature_image(accountant_sig) if accountant_name else ''
        
        if accountant_name:
            rows.append([self._p_center('DECLARANTE', bold=True), '', '', self._p_center(title_acc, bold=True), '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (2, row_idx)),
                ('SPAN', (3, row_idx), (5, row_idx)),
                ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SUBHEADER),
            ])
            row_idx += 1
            
            rows.append([declarant_sig_el, '', '', accountant_sig_el, '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (2, row_idx)),
                ('SPAN', (3, row_idx), (5, row_idx)),
                ('ALIGN', (0, row_idx), (5, row_idx), 'CENTER'),
                ('VALIGN', (0, row_idx), (5, row_idx), 'MIDDLE'),
            ])
            row_idx += 1
            
            rows.append([self._p_small(f'Nombre: {declarant_name}'), '', '', self._p_small(f'Nombre: {accountant_name}'), '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (2, row_idx)),
                ('SPAN', (3, row_idx), (5, row_idx)),
            ])
            row_idx += 1
            
            rows.append([self._p_small(f'Doc: {declarant_doc}'), '', '', self._p_small(f'T.P.: {accountant_card}'), '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (2, row_idx)),
                ('SPAN', (3, row_idx), (5, row_idx)),
            ])
            row_idx += 1
        else:
            rows.append([self._p_center('FIRMA DEL DECLARANTE / REPRESENTANTE LEGAL', bold=True), '', '', '', '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (5, row_idx)),
                ('BACKGROUND', (0, row_idx), (5, row_idx), COLOR_SUBHEADER),
            ])
            row_idx += 1
            
            rows.append([declarant_sig_el, '', '', '', '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (5, row_idx)),
                ('ALIGN', (0, row_idx), (5, row_idx), 'CENTER'),
                ('VALIGN', (0, row_idx), (5, row_idx), 'MIDDLE'),
            ])
            row_idx += 1
            
            rows.append([
                self._p_label('Nombre:'), self._p(declarant_name),
                self._p_label('Doc:'), self._p(declarant_doc),
                self._p_label('Fecha:'), self._p(declaration_date or '________')
            ])
            styles.extend([
                ('BACKGROUND', (0, row_idx), (0, row_idx), COLOR_SUBHEADER),
                ('BACKGROUND', (2, row_idx), (2, row_idx), COLOR_SUBHEADER),
                ('BACKGROUND', (4, row_idx), (4, row_idx), COLOR_SUBHEADER),
            ])
            row_idx += 1
        
        # Información de integridad
        if data.get('is_signed'):
            signed_at = signature_info.get('signed_at') or data.get('signed_at', '')
            integrity_hash = data.get('integrity_hash', '')
            hash_short = (integrity_hash[:16] + '...') if len(integrity_hash) > 16 else integrity_hash
            
            rows.append([self._p_small(f'Firmado: {signed_at}'), '', '', self._p_small(f'Hash: {hash_short}'), '', ''])
            styles.extend([
                ('SPAN', (0, row_idx), (2, row_idx)),
                ('SPAN', (3, row_idx), (5, row_idx)),
            ])
            row_idx += 1
        
        # ===================== CREAR TABLA =====================
        table = Table(rows, colWidths=col_widths)
        
        # Estilos globales
        base_styles = [
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
            ('TOPPADDING', (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Aplicar todos los estilos
        table.setStyle(TableStyle(base_styles + styles))
        
        return table
    
    def _create_signature_image(self, signature_data: str):
        """Crea elemento de imagen de firma desde base64."""
        if signature_data and signature_data.startswith('data:image'):
            try:
                signature_base64 = signature_data.split(',')[1]
                signature_bytes = base64.b64decode(signature_base64)
                signature_buffer = BytesIO(signature_bytes)
                return Image(signature_buffer, width=1.5*inch, height=0.4*inch)
            except:
                pass
        return Paragraph('<font size="6">_________________________</font>', 
                        ParagraphStyle('sig', alignment=TA_CENTER))
    
    def _build_footer(self) -> list:
        elements = []
        elements.append(Spacer(1, 2))
        
        legal_notes = self.config.get('legal_notes', '')
        if legal_notes:
            elements.append(Paragraph(legal_notes, self.styles['Footer']))
        
        footer_text = self.config.get('footer_text', '')
        if footer_text:
            elements.append(Paragraph(footer_text, self.styles['Footer']))
        
        timestamp = get_colombia_time().strftime('%Y-%m-%d %H:%M:%S')
        elements.append(Paragraph(f'Generado: {timestamp} (Hora Colombia)', self.styles['Footer']))
        
        return elements
    
    def _build_activities_annex(self, activities: list) -> list:
        """Construye página de anexo con detalle de actividades."""
        elements = []
        
        if not activities:
            return elements
        
        elements.append(Paragraph('ANEXO – Detalle de Actividades Gravadas', self.styles['FormTitle']))
        elements.append(Spacer(1, 4))
        
        col_widths = [0.35*inch, 0.7*inch, 2.9*inch, 1.1*inch, 0.6*inch, 1.0*inch]
        
        rows = [[
            self._p_center('#', bold=True),
            self._p_center('Código', bold=True),
            self._p_center('Descripción', bold=True),
            self._p_center('Ingresos', bold=True),
            self._p_center('Tarifa‰', bold=True),
            self._p_center('Impuesto', bold=True)
        ]]
        
        total_tax = 0
        for i, act in enumerate(activities, start=1):
            income = act.get('income', 0) or 0
            rate = act.get('tax_rate', 0) or 0
            tax = income * rate / 100  # Porcentaje
            total_tax += tax
            
            desc = act.get('description', '') or ''
            if len(desc) > 50:
                desc = desc[:47] + '...'
            
            rows.append([
                self._p_center(str(i)),
                self._p(act.get('ciiu_code', '')),
                self._p(desc),
                self._p_right(self._fmt(income)),
                self._p_center(f"{rate:.2f}"),
                self._p_right(self._fmt(tax))
            ])
        
        rows.append([
            self._p(''), self._p(''),
            self._p_bold('TOTAL IMPUESTO POR ACTIVIDADES'),
            self._p(''), self._p(''),
            self._p_right(self._fmt(total_tax), bold=True)
        ])
        
        table = Table(rows, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRID),
            ('TOPPADDING', (0, 0), (-1, -1), PAD),
            ('BOTTOMPADDING', (0, 0), (-1, -1), PAD),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, -1), (-1, -1), COLOR_GREEN),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 4))
        elements.append(Paragraph('<i>Este anexo forma parte integral del formulario ICA.</i>', self.styles['Footer']))
        
        return elements
