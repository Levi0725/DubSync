"""
DubSync PDF Export

Professzionális szinkronszövegkönyv PDF generálás.

A generált PDF a klasszikus magyar szinkronszövegkönyv formátumot követi:
- Fejléc projekt információkkal
- Táblázatos elrendezés
- Időkód, karakter, szöveg, megjegyzések, SFX
- Oldaltörések cue-k szerint
- Nyomtatásbarát formátum
"""

from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dubsync.models.cue import Cue
from dubsync.models.project import Project

if TYPE_CHECKING:
    from dubsync.models.database import Database


class PDFExporter:
    """
    Szinkronszövegkönyv PDF exportáló.
    
    A generált PDF nem tartalmaz technikai adatokat (lip-sync, státusz),
    csak a felvételhez szükséges szöveget.
    """
    
    # Page settings
    PAGE_SIZE = A4
    MARGIN_LEFT = 20 * mm
    MARGIN_RIGHT = 20 * mm
    MARGIN_TOP = 25 * mm
    MARGIN_BOTTOM = 20 * mm
    
    # Column widths (A4 width ~= 210mm, content ~= 170mm)
    COL_TIME = 30 * mm
    COL_MAIN = 110 * mm
    COL_NOTES = 30 * mm
    
    def __init__(self, db: Optional["Database"] = None):
        """
        Inicializálás.
        
        Args:
            db: Adatbázis kapcsolat (opcionális)
        """
        self.db = db
        self.styles = self._create_styles()
        self._register_fonts()
    
    def _register_fonts(self):
        """
        Font regisztráció magyar karakterekhez.
        
        Próbálja a Windows rendszer fontjait használni.
        """
        try:
            # Try to use Arial for better Hungarian support
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
            self.font_name = 'Arial'
            self.font_bold = 'Arial-Bold'
        except Exception:
            # Fallback to Helvetica
            self.font_name = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'
    
    def _create_styles(self) -> dict:
        """
        Stílusok létrehozása.
        """
        styles = getSampleStyleSheet()

        return {
            'Title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=6 * mm,
                alignment=TA_CENTER,
            ),
            'Subtitle': ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=3 * mm,
                alignment=TA_CENTER,
            ),
            'Header': ParagraphStyle(
                'CustomHeader',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.grey,
                alignment=TA_RIGHT,
            ),
            'TimeCode': ParagraphStyle(
                'TimeCode',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_LEFT,
            ),
            'Character': ParagraphStyle(
                'Character',
                parent=styles['Normal'],
                fontSize=10,
                fontName='Helvetica-Bold',
            ),
            'DialogText': ParagraphStyle(
                'DialogText',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
            ),
            'Notes': ParagraphStyle(
                'Notes',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.darkgrey,
                fontName='Helvetica-Oblique',
            ),
            'SFX': ParagraphStyle(
                'SFX',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.darkblue,
            ),
            'Footer': ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER,
            ),
        }
    
    def export(
        self,
        output_path: Path,
        project: Project,
        cues: List[Cue],
        include_source: bool = False,
    ) -> None:
        """
        PDF exportálás.
        
        Args:
            output_path: Kimeneti fájl elérési útja
            project: Projekt objektum
            cues: Cue lista
            include_source: Forrásszöveg is legyen benne
        """
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.PAGE_SIZE,
            leftMargin=self.MARGIN_LEFT,
            rightMargin=self.MARGIN_RIGHT,
            topMargin=self.MARGIN_TOP,
            bottomMargin=self.MARGIN_BOTTOM,
        )
        
        # Build story
        story = []
        
        # Add header
        story.extend(self._create_header(project))
        story.append(Spacer(1, 10 * mm))
        
        # Add cues
        story.extend(self._create_cue_table(cues, include_source))
        
        # Build PDF
        doc.build(
            story,
            onFirstPage=self._add_page_header,
            onLaterPages=self._add_page_header,
        )
    
    def _create_header(self, project: Project) -> List[Flowable]:
        """
        Fejléc létrehozása projekt adatokkal.
        """
        # Main title
        if project.series_title:
            title = project.series_title
            if project.title and project.title != "Új projekt":
                title += f" - {project.title}"
        else:
            title = project.title or "Szinkronszövegkönyv"

        elements: List[Flowable] = [Paragraph(title, self.styles['Title'])]
        # Season/Episode
        if project.season or project.episode:
            season_ep = []
            if project.season:
                season_ep.append(f"{project.season}. évad")
            if project.episode:
                season_ep.append(f"{project.episode}. rész")
            elements.append(Paragraph(
                " / ".join(season_ep),
                self.styles['Subtitle']
            ))

        # Credits
        credits = []
        if project.translator:
            credits.append(f"Fordította: {project.translator}")
        if project.editor:
            credits.append(f"Lektor: {project.editor}")

        if credits:
            elements.append(Paragraph(
                " | ".join(credits),
                self.styles['Subtitle']
            ))

        # Separator line
        elements.append(Spacer(1, 5 * mm))

        # Table header
        header_data = [["IDŐ", "SZÖVEG", "EGYÉB"]]
        header_table = Table(
            header_data,
            colWidths=[self.COL_TIME, self.COL_MAIN, self.COL_NOTES]
        )
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.font_bold),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('BACKGROUND', (0, 0), (-1, -1), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(header_table)

        return elements
    
    def _create_cue_table(self, cues: List[Cue], include_source: bool) -> List:
        """
        Cue táblázat létrehozása.
        """
        elements = []
        
        for cue in cues:
            row = self._create_cue_row(cue, include_source)
            elements.append(KeepTogether(row))
        
        return elements
    
    def _create_cue_row(self, cue: Cue, include_source: bool) -> Table:
        """
        Egyetlen cue sor létrehozása.
        """
        # Time column
        time_text = f"{cue.time_in_timecode[:8]}\n{cue.time_out_timecode[:8]}"
        time_para = Paragraph(
            time_text.replace('\n', '<br/>'),
            self.styles['TimeCode']
        )

        # Main text column
        main_parts = []

        # Character name
        if cue.character_name:
            main_parts.append(Paragraph(
                f"[{cue.character_name}]:",
                self.styles['Character']
            ))

        if text := cue.translated_text or cue.source_text:
            # Replace newlines with <br/>
            text = text.replace('\n', '<br/>')
            main_parts.append(Paragraph(text, self.styles['DialogText']))

        # Source text
        if include_source and cue.translated_text and cue.source_text:
            source = cue.source_text.replace('\n', '<br/>')
            main_parts.append(Paragraph(
                f"<i>[Eredeti: {source}]</i>",
                self.styles['Notes']
            ))

        # Notes (non-technical)
        if cue.notes:
            notes = cue.notes.replace('\n', '<br/>')
            main_parts.append(Paragraph(
                f"({notes})",
                self.styles['Notes']
            ))

        # Notes/SFX column
        sfx_parts = []

        if cue.sfx_notes:
            sfx = cue.sfx_notes.replace('\n', '<br/>')
            sfx_parts.append(Paragraph(sfx, self.styles['SFX']))

        # Build row data
        data = [[
            time_para,
            main_parts or '',
            sfx_parts or '',
        ]]

        # Create table
        table = Table(
            data,
            colWidths=[self.COL_TIME, self.COL_MAIN, self.COL_NOTES]
        )

        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))

        return table
    
    def _add_page_header(self, canvas, doc):
        """
        Oldalszámozás és élőfej.
        """
        canvas.saveState()
        
        # Page number
        page_num = canvas.getPageNumber()
        text = f"- {page_num} -"
        canvas.setFont(self.font_name, 9)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            self.PAGE_SIZE[0] / 2,
            self.MARGIN_BOTTOM / 2,
            text
        )
        
        # Date on first page
        if page_num == 1:
            date_str = datetime.now().strftime("%Y. %m. %d.")
            canvas.drawRightString(
                self.PAGE_SIZE[0] - self.MARGIN_RIGHT,
                self.PAGE_SIZE[1] - 15 * mm,
                date_str
            )
        
        canvas.restoreState()


def export_to_pdf(
    output_path: Path,
    project: Project,
    cues: List[Cue],
    include_source: bool = False,
) -> None:
    """
    Convenience function PDF exportáláshoz.
    
    Args:
        output_path: Kimeneti fájl elérési útja
        project: Projekt objektum
        cues: Cue lista
        include_source: Forrásszöveg is legyen benne
    """
    exporter = PDFExporter()
    exporter.export(output_path, project, cues, include_source)
