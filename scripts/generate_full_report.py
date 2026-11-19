"""
Compressed (~30-Page) Document Generator for Ticket-to-Topology (t2t) B.Tech Project Report.
Follows all Chandubhai S. Patel Institute of Technology (CSPIT), CHARUSAT guidelines:
- A4 size, 1.25" Left margin, 1.0" Right/Top/Bottom margins.
- Times New Roman font throughout (16pt Chapter, 14pt Section, 12pt Subsection, 12pt Body).
- 1.5 line spacing, Justified paragraphs.
- Proper Captioning: Table above (Table X.Y Name), Figure below (Fig X.Y Name).
- Sequential figure numbering (Fig 2.1, Fig 3.1, Fig 4.1-4.4, Fig 5.1-5.4).
- Section 5.1.1 (Method Pseudo Code) removed cleanly per user requirement.
- Structured 3-column Table of Content, List of Figures, and List of Tables.
- Two-pass MS Word COM auto-pagination (if Microsoft Word is installed on Windows)
  to guarantee 100% exact rendered page numbers in TOC, List of Figures, and List of Tables.
"""

from pathlib import Path
import subprocess
import json
import sys
import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

ROOT_DIR = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT_DIR / "reports" / "figures"
OUT_PATH = ROOT_DIR / "reports" / "Ticket_To_Topology_Project_Report.docx"

PROJECT_ID = "CSPIT/CSE/7TH/T2T-2026"
CANDIDATE_NAME = "Jeet Dhaduk"
CANDIDATE_ID = "D24CS124"
PROJECT_TITLE = (
    "TICKET-TO-TOPOLOGY (T2T): CCNP ENTERPRISE EIGRP-OSPF MUTUAL ROUTE "
    "REDISTRIBUTION SIMULATOR & STATIC AUDIT PLATFORM"
)
PROJECT_SUBTITLE = (
    "An Automated Verification, AST-Based Configuration Linting, and Pedagogical "
    "Socratic Troubleshooting Environment for Cisco IOS-XE Networks"
)

# Default calibrated page map (automatically replaced by exact Word page numbers when Word COM is available)
DEFAULT_PAGE_MAP = {
    # Prelims (Roman)
    "ABSTRACT": "i",
    "ACKNOWLEDGEMENT": "ii",
    "TABLE OF CONTENT": "iii",
    "LIST OF FIGURES": "v",
    "LIST OF TABLES": "vi",
    # Chapters & Sections (Arabic)
    "CHAPTER 1: INTRODUCTION": "1",
    "1.1 PROJECT SUMMARY": "1",
    "1.2 PURPOSE": "1",
    "1.3 OBJECTIVE": "2",
    "1.4 SCOPE": "2",
    "1.4.1 In-Scope Capabilities": "2",
    "1.4.2 Out-of-Scope Capabilities": "2",
    "1.5 TECHNOLOGY AND LITERATURE REVIEW": "3",
    "CHAPTER 2: PROJECT MANAGEMENT": "4",
    "2.1 PROJECT PLANNING": "4",
    "2.1.1 Project Development Approach and Justification": "4",
    "2.1.2 Project Effort, Time, and Cost Estimation": "5",
    "2.1.3 Roles and Responsibilities": "5",
    "2.1.4 Group Dependencies": "6",
    "2.2 PROJECT SCHEDULING": "6",
    "CHAPTER 3: SYSTEM REQUIREMENTS STUDY": "7",
    "3.1 USER CHARACTERISTICS": "7",
    "3.2 HARDWARE AND SOFTWARE REQUIREMENTS": "8",
    "3.3 ASSUMPTIONS AND DEPENDENCIES": "9",
    "CHAPTER 4: SYSTEM ANALYSIS": "10",
    "4.1 STUDY OF CURRENT SYSTEM": "10",
    "4.2 PROBLEM AND WEAKNESSES OF CURRENT SYSTEM": "10",
    "4.3 REQUIREMENTS OF NEW SYSTEM": "11",
    "4.3.1 Functional Requirements": "11",
    "4.3.2 Non-Functional Requirements": "12",
    "4.4 FEASIBILITY STUDY": "13",
    "4.4.1 Organizational Objectives Contribution": "13",
    "4.4.2 Technical and Schedule Feasibility": "13",
    "4.4.3 System Integration Feasibility": "13",
    "4.5 ACTIVITY / PROCESS IN NEW SYSTEM": "14",
    "4.6 FEATURES OF NEW SYSTEM": "14",
    "4.7 USE CASE DIAGRAM & DESCRIPTIONS": "15",
    "4.8 CLASS DIAGRAM": "16",
    "4.9 SEQUENCE DIAGRAM": "17",
    "CHAPTER 5: SYSTEM DESIGN": "18",
    "5.1 SYSTEM APPLICATION DESIGN": "18",
    "5.2 INPUT / OUTPUT AND INTERFACE DESIGN": "19",
    "5.2.1 Samples of Forms, Reports, and Interface": "19",
    "5.2.2 State Diagram": "20",
    "5.3 SYSTEM STRUCTURAL DESIGN & DATABASE SCHEMA": "21",
    "CHAPTER 6: IMPLEMENTATION PLANNING": "22",
    "6.1 IMPLEMENTATION ENVIRONMENT": "22",
    "6.2 MODULES SPECIFICATION": "22",
    "6.3 SECURITY FEATURES": "23",
    "6.4 CODING STANDARDS": "23",
    "CHAPTER 7: TESTING": "24",
    "7.1 TESTING PLAN": "24",
    "7.2 TESTING STRATEGY": "24",
    "7.3 TEST SUITES DESIGN & VERIFICATION EXECUTION": "25",
    "CHAPTER 8: CONCLUSION AND DISCUSSION": "26",
    "8.1 SELF-ANALYSIS OF PROJECT VIABILITIES": "26",
    "8.2 PROBLEMS ENCOUNTERED AND POSSIBLE SOLUTIONS": "27",
    "8.3 SUMMARY OF PROJECT WORK": "28",
    "CHAPTER 9: LIMITATION AND FUTURE ENHANCEMENT": "29",
    "9.1 PROJECT LIMITATIONS": "29",
    "9.2 FUTURE ENHANCEMENTS": "29",
    "REFERENCES": "30",
    # Figures (exact sequential order)
    "Fig 2.1 Gantt Chart (14-Week Development Schedule)": "6",
    "Fig 3.1 System Use Case Diagram": "7",
    "Fig 4.1 Ticket-to-Topology (t2t) Multi-Tier System Architecture": "11",
    "Fig 4.2 End-to-End Troubleshooting Activity Process Flow": "14",
    "Fig 4.3 High-Level Unified Class Diagram (OOP Design)": "16",
    "Fig 4.4 Sequence Diagram: Verification & Socratic Guidance Lifecycle": "17",
    "Fig 5.1 CCNP Enterprise Dual-Point Mutual Route Redistribution Topology": "18",
    "Fig 5.2 FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas": "19",
    "Fig 5.3 Finite State Machine (FSM) Lifecycle Diagram": "20",
    "Fig 5.4 SQLite WAL Session Store Entity-Relationship (ER) Schema": "21",
    # Tables
    "Table 1.1 Tools and Technologies Used": "3",
    "Table 2.1 Project Planning Breakdown (14-Week Schedule)": "4",
    "Table 2.2 COCOMO-II Effort & Resource Estimation": "5",
    "Table 2.3 Roles and Module Ownership": "5",
    "Table 3.1 User Characteristics Matrix": "7",
    "Table 3.2 Hardware & Software Requirements Specification": "8",
    "Table 3.3 Assumptions and Technical Dependencies": "9",
    "Table 4.1 Comparative Analysis: Existing Approaches vs Ticket-to-Topology (t2t)": "10",
    "Table 4.2 Functional Requirements (FR1 to FR12)": "11",
    "Table 4.3 Non-Functional Requirements (NFR1 to NFR8)": "12",
    "Table 4.4 Use Case Specifications": "15",
    "Table 4.5 Core Object Classes and Method Contracts": "16",
    "Table 5.1 Database Schema Dictionary (SQLite WAL Mode)": "21",
    "Table 6.1 Module Architecture Specifications": "22",
    "Table 6.2 Security Controls & Compliance Matrix": "23",
    "Table 7.1 Testing Strategy and Methodology Matrix": "24",
    "Table 7.2 Comprehensive Test Suites & Verification Execution Results (U1.1 to U10.3)": "25",
    "Table 8.1 Self-Analysis of Project Viabilities": "26",
    "Table 8.2 Technical Obstacles Encountered and Engineering Solutions": "27",
}

TOC_SPEC = [
    ("—", "Abstract", "ABSTRACT", False),
    ("—", "Acknowledgement", "ACKNOWLEDGEMENT", False),
    ("—", "Table of Content", "TABLE OF CONTENT", False),
    ("—", "List of Figures", "LIST OF FIGURES", False),
    ("—", "List of Tables", "LIST OF TABLES", False),
    ("Chapter 1", "Introduction", "CHAPTER 1: INTRODUCTION", True),
    ("1.1", "Project Summary", "1.1 PROJECT SUMMARY", False),
    ("1.2", "Purpose", "1.2 PURPOSE", False),
    ("1.3", "Objective", "1.3 OBJECTIVE", False),
    ("1.4", "Scope", "1.4 SCOPE", False),
    ("1.4.1", "In-Scope Capabilities", "1.4.1 In-Scope Capabilities", False),
    ("1.4.2", "Out-of-Scope Capabilities", "1.4.2 Out-of-Scope Capabilities", False),
    ("1.5", "Technology and Literature Review", "1.5 TECHNOLOGY AND LITERATURE REVIEW", False),
    ("Chapter 2", "Project Management", "CHAPTER 2: PROJECT MANAGEMENT", True),
    ("2.1", "Project Planning", "2.1 PROJECT PLANNING", False),
    ("2.1.1", "Project Development Approach and Justification", "2.1.1 Project Development Approach and Justification", False),
    ("2.1.2", "Project Effort, Time, and Cost Estimation", "2.1.2 Project Effort, Time, and Cost Estimation", False),
    ("2.1.3", "Roles and Responsibilities", "2.1.3 Roles and Responsibilities", False),
    ("2.1.4", "Group Dependencies", "2.1.4 Group Dependencies", False),
    ("2.2", "Project Scheduling", "2.2 PROJECT SCHEDULING", False),
    ("Chapter 3", "System Requirements Study", "CHAPTER 3: SYSTEM REQUIREMENTS STUDY", True),
    ("3.1", "User Characteristics", "3.1 USER CHARACTERISTICS", False),
    ("3.2", "Hardware and Software Requirements", "3.2 HARDWARE AND SOFTWARE REQUIREMENTS", False),
    ("3.3", "Assumptions and Dependencies", "3.3 ASSUMPTIONS AND DEPENDENCIES", False),
    ("Chapter 4", "System Analysis", "CHAPTER 4: SYSTEM ANALYSIS", True),
    ("4.1", "Study of Current System", "4.1 STUDY OF CURRENT SYSTEM", False),
    ("4.2", "Problem and Weaknesses of Current System", "4.2 PROBLEM AND WEAKNESSES OF CURRENT SYSTEM", False),
    ("4.3", "Requirements of New System", "4.3 REQUIREMENTS OF NEW SYSTEM", False),
    ("4.3.1", "Functional Requirements", "4.3.1 Functional Requirements", False),
    ("4.3.2", "Non-Functional Requirements", "4.3.2 Non-Functional Requirements", False),
    ("4.4", "Feasibility Study", "4.4 FEASIBILITY STUDY", False),
    ("4.4.1", "Organizational Objectives Contribution", "4.4.1 Organizational Objectives Contribution", False),
    ("4.4.2", "Technical and Schedule Feasibility", "4.4.2 Technical and Schedule Feasibility", False),
    ("4.4.3", "System Integration Feasibility", "4.4.3 System Integration Feasibility", False),
    ("4.5", "Activity / Process in New System", "4.5 ACTIVITY / PROCESS IN NEW SYSTEM", False),
    ("4.6", "Features of New System", "4.6 FEATURES OF NEW SYSTEM", False),
    ("4.7", "Use Case Diagram & Descriptions", "4.7 USE CASE DIAGRAM & DESCRIPTIONS", False),
    ("4.8", "Class Diagram", "4.8 CLASS DIAGRAM", False),
    ("4.9", "Sequence Diagram", "4.9 SEQUENCE DIAGRAM", False),
    ("Chapter 5", "System Design", "CHAPTER 5: SYSTEM DESIGN", True),
    ("5.1", "System Application Design", "5.1 SYSTEM APPLICATION DESIGN", False),
    ("5.2", "Input / Output and Interface Design", "5.2 INPUT / OUTPUT AND INTERFACE DESIGN", False),
    ("5.2.1", "Samples of Forms, Reports, and Interface", "5.2.1 Samples of Forms, Reports, and Interface", False),
    ("5.2.2", "State Diagram", "5.2.2 State Diagram", False),
    ("5.3", "System Structural Design & Database Schema", "5.3 SYSTEM STRUCTURAL DESIGN & DATABASE SCHEMA", False),
    ("Chapter 6", "Implementation Planning", "CHAPTER 6: IMPLEMENTATION PLANNING", True),
    ("6.1", "Implementation Environment", "6.1 IMPLEMENTATION ENVIRONMENT", False),
    ("6.2", "Modules Specification", "6.2 MODULES SPECIFICATION", False),
    ("6.3", "Security Features", "6.3 SECURITY FEATURES", False),
    ("6.4", "Coding Standards", "6.4 CODING STANDARDS", False),
    ("Chapter 7", "Testing", "CHAPTER 7: TESTING", True),
    ("7.1", "Testing Plan", "7.1 TESTING PLAN", False),
    ("7.2", "Testing Strategy", "7.2 TESTING STRATEGY", False),
    ("7.3", "Test Suites Design & Verification Execution", "7.3 TEST SUITES DESIGN & VERIFICATION EXECUTION", False),
    ("Chapter 8", "Conclusion and Discussion", "CHAPTER 8: CONCLUSION AND DISCUSSION", True),
    ("8.1", "Self-Analysis of Project Viabilities", "8.1 SELF-ANALYSIS OF PROJECT VIABILITIES", False),
    ("8.2", "Problems Encountered and Possible Solutions", "8.2 PROBLEMS ENCOUNTERED AND POSSIBLE SOLUTIONS", False),
    ("8.3", "Summary of Project Work", "8.3 SUMMARY OF PROJECT WORK", False),
    ("Chapter 9", "Limitation and Future Enhancement", "CHAPTER 9: LIMITATION AND FUTURE ENHANCEMENT", True),
    ("9.1", "Project Limitations", "9.1 PROJECT LIMITATIONS", False),
    ("9.2", "Future Enhancements", "9.2 FUTURE ENHANCEMENTS", False),
    ("—", "References", "REFERENCES", True),
]

FIGURES_SPEC = [
    ("Fig 2.1", "Gantt Chart (14-Week Development Schedule)", "Fig 2.1 Gantt Chart (14-Week Development Schedule)"),
    ("Fig 3.1", "System Use Case Diagram", "Fig 3.1 System Use Case Diagram"),
    ("Fig 4.1", "Ticket-to-Topology (t2t) Multi-Tier System Architecture", "Fig 4.1 Ticket-to-Topology (t2t) Multi-Tier System Architecture"),
    ("Fig 4.2", "End-to-End Troubleshooting Activity Process Flow", "Fig 4.2 End-to-End Troubleshooting Activity Process Flow"),
    ("Fig 4.3", "High-Level Unified Class Diagram (OOP Design)", "Fig 4.3 High-Level Unified Class Diagram (OOP Design)"),
    ("Fig 4.4", "Sequence Diagram: Verification & Socratic Guidance Lifecycle", "Fig 4.4 Sequence Diagram: Verification & Socratic Guidance Lifecycle"),
    ("Fig 5.1", "CCNP Enterprise Dual-Point Mutual Route Redistribution Topology", "Fig 5.1 CCNP Enterprise Dual-Point Mutual Route Redistribution Topology"),
    ("Fig 5.2", "FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas", "Fig 5.2 FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas"),
    ("Fig 5.3", "Finite State Machine (FSM) Lifecycle Diagram", "Fig 5.3 Finite State Machine (FSM) Lifecycle Diagram"),
    ("Fig 5.4", "SQLite WAL Session Store Entity-Relationship (ER) Schema", "Fig 5.4 SQLite WAL Session Store Entity-Relationship (ER) Schema"),
]

TABLES_SPEC = [
    ("Table 1.1", "Tools and Technologies Used", "Table 1.1 Tools and Technologies Used"),
    ("Table 2.1", "Project Planning Breakdown (14-Week Schedule)", "Table 2.1 Project Planning Breakdown (14-Week Schedule)"),
    ("Table 2.2", "COCOMO-II Effort & Resource Estimation", "Table 2.2 COCOMO-II Effort & Resource Estimation"),
    ("Table 2.3", "Roles and Module Ownership", "Table 2.3 Roles and Module Ownership"),
    ("Table 3.1", "User Characteristics Matrix", "Table 3.1 User Characteristics Matrix"),
    ("Table 3.2", "Hardware & Software Requirements Specification", "Table 3.2 Hardware & Software Requirements Specification"),
    ("Table 3.3", "Assumptions and Technical Dependencies", "Table 3.3 Assumptions and Technical Dependencies"),
    ("Table 4.1", "Comparative Analysis: Existing Approaches vs Ticket-to-Topology (t2t)", "Table 4.1 Comparative Analysis: Existing Approaches vs Ticket-to-Topology (t2t)"),
    ("Table 4.2", "Functional Requirements (FR1 to FR12)", "Table 4.2 Functional Requirements (FR1 to FR12)"),
    ("Table 4.3", "Non-Functional Requirements (NFR1 to NFR8)", "Table 4.3 Non-Functional Requirements (NFR1 to NFR8)"),
    ("Table 4.4", "Use Case Specifications", "Table 4.4 Use Case Specifications"),
    ("Table 4.5", "Core Object Classes and Method Contracts", "Table 4.5 Core Object Classes and Method Contracts"),
    ("Table 5.1", "Database Schema Dictionary (SQLite WAL Mode)", "Table 5.1 Database Schema Dictionary (SQLite WAL Mode)"),
    ("Table 6.1", "Module Architecture Specifications", "Table 6.1 Module Architecture Specifications"),
    ("Table 6.2", "Security Controls & Compliance Matrix", "Table 6.2 Security Controls & Compliance Matrix"),
    ("Table 7.1", "Testing Strategy and Methodology Matrix", "Table 7.1 Testing Strategy and Methodology Matrix"),
    ("Table 7.2", "Comprehensive Test Suites & Verification Execution Results (U1.1 to U10.3)", "Table 7.2 Comprehensive Test Suites & Verification Execution Results (U1.1 to U10.3)"),
    ("Table 8.1", "Self-Analysis of Project Viabilities", "Table 8.1 Self-Analysis of Project Viabilities"),
    ("Table 8.2", "Technical Obstacles Encountered and Engineering Solutions", "Table 8.2 Technical Obstacles Encountered and Engineering Solutions"),
]


def to_roman(num: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for v, sym in vals:
        while num >= v:
            out.append(sym)
            num -= v
    return "".join(out)


def create_report(page_map: dict[str, str]) -> Path:
    doc = docx.Document()

    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.5
    normal_style.paragraph_format.space_after = Pt(4)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_xml_field(run, field_name):
        fldChar1 = OxmlElement("w:fldChar")
        fldChar1.set(qn("w:fldCharType"), "begin")
        instrText = OxmlElement("w:instrText")
        instrText.set(qn("xml:space"), "preserve")
        instrText.text = field_name
        fldChar2 = OxmlElement("w:fldChar")
        fldChar2.set(qn("w:fldCharType"), "separate")
        fldChar3 = OxmlElement("w:fldChar")
        fldChar3.set(qn("w:fldCharType"), "end")
        r = run._r
        r.append(fldChar1)
        r.append(instrText)
        r.append(fldChar2)
        r.append(fldChar3)

    def set_section_margins(sec):
        sec.page_width = Mm(210)
        sec.page_height = Mm(297)
        sec.left_margin = Inches(1.25)
        sec.right_margin = Inches(1.0)
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)

    def set_page_number_type(section, fmt="decimal", start=None):
        sectPr = section._sectPr
        for child in list(sectPr):
            if child.tag.endswith("pgNumType"):
                sectPr.remove(child)
        pgNumType = OxmlElement("w:pgNumType")
        pgNumType.set(qn("w:fmt"), fmt)
        if start is not None:
            pgNumType.set(qn("w:start"), str(start))
        sectPr.append(pgNumType)

    def set_cell_margins(cell, top=55, bottom=55, left=90, right=90):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(
            f'<w:tcMar {nsdecls("w")}>'
            f'<w:top w:w="{top}" w:type="dxa"/>'
            f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
            f'<w:left w:w="{left}" w:type="dxa"/>'
            f'<w:right w:w="{right}" w:type="dxa"/>'
            f"</w:tcMar>"
        )
        tcPr.append(tcMar)

    def format_table_borders(table, color="B0B0B0"):
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{color}"/>'
            f"</w:tblBorders>"
        )
        tblPr.append(borders)

    def style_header_footer(section, right_title, is_roman=False, start_num=None):
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False
        set_page_number_type(section, fmt="lowerRoman" if is_roman else "decimal", start=start_num)

        hdr_tbl = section.header.add_table(rows=1, cols=2, width=Inches(6.02))
        hdr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        c1, c2 = hdr_tbl.rows[0].cells
        c1.paragraphs[0].text = PROJECT_ID
        c1.paragraphs[0].runs[0].font.name = "Times New Roman"
        c1.paragraphs[0].runs[0].font.size = Pt(9.5)
        c1.paragraphs[0].runs[0].font.color.rgb = RGBColor(90, 90, 90)

        c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        c2.paragraphs[0].text = right_title
        c2.paragraphs[0].runs[0].font.name = "Times New Roman"
        c2.paragraphs[0].runs[0].font.size = Pt(9.5)
        c2.paragraphs[0].runs[0].font.color.rgb = RGBColor(90, 90, 90)

        ftr_tbl = section.footer.add_table(rows=1, cols=3, width=Inches(6.02))
        ftr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        fc1, fc2, fc3 = ftr_tbl.rows[0].cells
        fc1.paragraphs[0].text = "CSPIT"
        fc1.paragraphs[0].runs[0].font.name = "Times New Roman"
        fc1.paragraphs[0].runs[0].font.size = Pt(9.5)
        fc1.paragraphs[0].runs[0].font.color.rgb = RGBColor(90, 90, 90)

        fc2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_num = fc2.paragraphs[0].add_run()
        r_num.font.name = "Times New Roman"
        r_num.font.size = Pt(9.5)
        r_num.font.color.rgb = RGBColor(90, 90, 90)
        add_xml_field(r_num, "PAGE")

        fc3.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fc3.paragraphs[0].text = "Department of Computer Science & Engineering"
        fc3.paragraphs[0].runs[0].font.name = "Times New Roman"
        fc3.paragraphs[0].runs[0].font.size = Pt(9.5)
        fc3.paragraphs[0].runs[0].font.color.rgb = RGBColor(90, 90, 90)

    def add_chapter_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(16)
        run.font.name = "Times New Roman"
        return p

    def add_section_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = "Times New Roman"
        return p

    def add_subsection_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(12)
        run.font.name = "Times New Roman"
        return p

    def add_body_p(text, bold_prefix=None, italic=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = "Times New Roman"
            r_pre.font.size = Pt(12)
        r_text = p.add_run(text)
        r_text.italic = italic
        r_text.font.name = "Times New Roman"
        r_text.font.size = Pt(12)
        return p

    def add_bullet_p(text, bold_prefix=None):
        p = doc.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(2.5)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = "Times New Roman"
            r_pre.font.size = Pt(12)
        r_text = p.add_run(text)
        r_text.font.name = "Times New Roman"
        r_text.font.size = Pt(12)
        return p

    def add_figure_image(filename, caption_num_name, width_in=5.1):
        img_path = FIG_DIR / filename
        if img_path.exists():
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(4)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.paragraph_format.keep_with_next = True
            p_img.add_run().add_picture(str(img_path), width=Inches(width_in))

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(1)
            p_cap.paragraph_format.space_after = Pt(8)
            r_cap = p_cap.add_run(caption_num_name)
            r_cap.bold = True
            r_cap.font.name = "Times New Roman"
            r_cap.font.size = Pt(10.5)

    def add_table_data(headers, rows, caption_num_name=None, col_widths=None, font_size=9.5, center_cols=(0,)):
        if caption_num_name:
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(6)
            p_cap.paragraph_format.space_after = Pt(3)
            p_cap.paragraph_format.keep_with_next = True
            r_cap = p_cap.add_run(caption_num_name)
            r_cap.bold = True
            r_cap.font.name = "Times New Roman"
            r_cap.font.size = Pt(10.5)

        tbl = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        format_table_borders(tbl)

        hdr_row = tbl.rows[0]
        hdr_row._tr.get_or_add_trPr().append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for idx, h_text in enumerate(headers):
            cell = hdr_row.cells[idx]
            set_cell_margins(cell, top=55, bottom=55, left=80, right=80)
            cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="E2E8F0"/>'))
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
            r = p.add_run(h_text)
            r.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(font_size + 0.5)

        for r_idx, row_data in enumerate(rows):
            row = tbl.rows[r_idx + 1]
            is_bold_row = False
            if isinstance(row_data, tuple) and len(row_data) == 2 and isinstance(row_data[1], bool):
                row_vals, is_bold_row = row_data
            else:
                row_vals = row_data
            bg_color = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
            for c_idx, cell_value in enumerate(row_vals):
                cell = row.cells[c_idx]
                set_cell_margins(cell, top=42, bottom=42, left=80, right=80)
                if bg_color != "FFFFFF":
                    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>'))
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.08
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx in center_cols else WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(str(cell_value))
                r.bold = is_bold_row
                r.font.name = "Times New Roman"
                r.font.size = Pt(font_size)

        if col_widths:
            for row in tbl.rows:
                for c_idx, w_in in enumerate(col_widths):
                    row.cells[c_idx].width = Inches(w_in)

        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_before = Pt(0)
        p_sp.paragraph_format.space_after = Pt(4)

    # ------------------------------------------------------------------
    # SECTION 1: COVER PAGE, INNER TITLE PAGE, DECLARATION, CERTIFICATE
    # ------------------------------------------------------------------
    s1 = doc.sections[0]
    set_section_margins(s1)
    s1.different_first_page_header_footer = False

    # Cover Page
    p_cov_top = doc.add_paragraph()
    p_cov_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_top.paragraph_format.space_before = Pt(24)
    p_cov_top.paragraph_format.space_after = Pt(8)
    r = p_cov_top.add_run("A\nPROJECT REPORT\nON")
    r.bold = True
    r.font.size = Pt(14)

    p_cov_title = doc.add_paragraph()
    p_cov_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_title.paragraph_format.space_before = Pt(10)
    p_cov_title.paragraph_format.space_after = Pt(8)
    r = p_cov_title.add_run(f'"{PROJECT_TITLE}"')
    r.bold = True
    r.font.size = Pt(15)

    p_cov_sub = doc.add_paragraph()
    p_cov_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_sub.paragraph_format.space_after = Pt(24)
    r = p_cov_sub.add_run(f"({PROJECT_SUBTITLE})")
    r.italic = True
    r.font.size = Pt(11)

    p_cov_prep = doc.add_paragraph()
    p_cov_prep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_prep.paragraph_format.space_after = Pt(6)
    p_cov_prep.add_run("Prepared by\n").font.size = Pt(12)
    r = p_cov_prep.add_run(f"{CANDIDATE_NAME} ({CANDIDATE_ID})")
    r.bold = True
    r.font.size = Pt(13)

    p_cov_sup = doc.add_paragraph()
    p_cov_sup.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_sup.paragraph_format.space_before = Pt(18)
    p_cov_sup.paragraph_format.space_after = Pt(22)
    p_cov_sup.add_run("Under the Supervision of\n").font.size = Pt(12)
    r = p_cov_sup.add_run("Prof. Harshul Yagnik / Dr. Amit Thakkar\n")
    r.bold = True
    r.font.size = Pt(12.5)
    p_cov_sup.add_run("Department of Computer Science & Engineering").font.size = Pt(11.5)

    p_cov_subm = doc.add_paragraph()
    p_cov_subm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cov_subm.paragraph_format.space_after = Pt(24)
    p_cov_subm.add_run(
        "Submitted to\n"
        "Charotar University of Science & Technology (CHARUSAT)\n"
        "for the Partial Fulfillment of the Requirements for the\n"
        "Degree of Bachelor of Technology (B.Tech.)\n"
        "in Computer Science & Engineering (Semester 7)"
    ).font.size = Pt(12)

    p_cov_inst = doc.add_paragraph()
    p_cov_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_cov_inst.add_run(
        "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING\n"
        "Chandubhai S. Patel Institute of Technology (CSPIT)\n"
        "Faculty of Technology & Engineering (FTE), CHARUSAT\n"
        "At: Changa, Dist: Anand, Pin: 388421, Gujarat, India\n"
        "Academic Year 2026-2027"
    )
    r.bold = True
    r.font.size = Pt(11.5)
    doc.add_page_break()

    # Candidate Declaration
    add_chapter_heading("CANDIDATE DECLARATION")
    add_body_p(
        f"I, {CANDIDATE_NAME} (Student ID: {CANDIDATE_ID}), hereby declare that the project report entitled "
        f'"{PROJECT_TITLE}" is a bonafide record of independent software architecture, network modeling, and '
        f"implementation carried out by me under the supervision of Prof. Harshul Yagnik, Department of Computer "
        f"Science & Engineering, Chandubhai S. Patel Institute of Technology (CSPIT), CHARUSAT."
    )
    add_body_p(
        "This work addresses multi-point mutual route redistribution anomalies across enterprise IP networks and has "
        "not been submitted, in part or in full, to any other university or institution for any degree or credential. "
        "The report strictly adheres to institutional UGC/AICTE anti-plagiarism norms (<35% overall similarity and "
        "<2% from any single source), with all third-party libraries and IETF RFC specifications duly cited."
    )
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(42)
    p_sig.add_run("Date: November 18, 2026\nPlace: CSPIT, CHARUSAT, Changa\n\n\n___________________________________\n").font.size = Pt(12)
    r = p_sig.add_run(f"{CANDIDATE_NAME} ({CANDIDATE_ID})\nB.Tech CSE - 7th Semester")
    r.bold = True
    r.font.size = Pt(12)
    doc.add_page_break()

    # Certificate
    add_chapter_heading("CERTIFICATE")
    add_body_p(
        f'This is to certify that the project report entitled "{PROJECT_TITLE}" is a bonafide work carried out by '
        f"{CANDIDATE_NAME} ({CANDIDATE_ID}) in partial fulfillment of the requirements for the degree of Bachelor of "
        f"Technology in Computer Science & Engineering (7th Semester) at Chandubhai S. Patel Institute of Technology "
        f"(CSPIT), Faculty of Technology & Engineering (FTE) – Charotar University of Science and Technology (CHARUSAT), Gujarat."
    )
    add_body_p(
        "To the best of our knowledge and belief, this work represents original technical development, verified "
        "automated testing, and reproducible lab engineering, and satisfies university standards for examination."
    )
    p_cert_sigs = doc.add_paragraph()
    p_cert_sigs.paragraph_format.space_before = Pt(64)
    r = p_cert_sigs.add_run(
        "Prof. Harshul Yagnik\t\t\t\tDr. Amit Thakkar\n"
        "Internal Project Supervisor\t\t\tHead of Department\n"
        "Assistant Professor, Dept. of CSE\t\tProfessor & Head, Dept. of CSE\n"
        "CSPIT, FTE, CHARUSAT\t\t\tCSPIT, FTE, CHARUSAT"
    )
    r.bold = True
    r.font.size = Pt(11)

    # ------------------------------------------------------------------
    # SECTION 2: PRELIMS (ROMAN NUMERALS i, ii, iii...)
    # ------------------------------------------------------------------
    s_abs = doc.add_section()
    set_section_margins(s_abs)
    style_header_footer(s_abs, "Abstract", is_roman=True, start_num=1)

    add_chapter_heading("ABSTRACT")
    add_body_p(
        "Enterprise IP networks routinely interconnect distinct Interior Gateway Protocol (IGP) domains using "
        "multi-point mutual route redistribution between Enhanced Interior Gateway Routing Protocol (EIGRP) and "
        "Open Shortest Path First (OSPF). Because these protocols use incompatible metrics and asymmetric default "
        "Administrative Distance (AD) values (EIGRP Internal 90, OSPF 110, EIGRP External 170), dual-boundary "
        "redistribution frequently causes circular route feedback loops, suboptimal transit paths, and prefix "
        "blackholing. Conventional CCNP Enterprise (ENCOR 350-401 and ENARSI 300-410) training relies on static "
        "workbooks or unguided emulators lacking deterministic grading and semantic configuration checks."
    )
    add_body_p(
        "This project presents Ticket-to-Topology (t2t), a dual-mode engineering platform uniting an interactive "
        "troubleshooting simulator with a production-grade static redistribution audit engine. Modeled on a "
        "four-router dual-ASBR topology (R1 Branch, R2/R3 ASBRs, R4 HQ), t2t parses Cisco IOS-XE running "
        "configurations into a hierarchical Abstract Syntax Tree (AST) and evaluates seven static audit rules "
        "(A1–A7) covering missing seed metrics, unbounded mutual redistribution, absent route tags, and AD "
        "inversion without modifying router state. For hands-on practice, a finite-state simulator injects seven "
        "parameterized faults (T1–T7) over live Netmiko SSH or deterministic offline mock replay fixtures."
    )
    add_body_p(
        "Candidate fixes are graded by a decoupled Verification Oracle that validates control-plane invariants "
        "without artificial intelligence. Guided assistance is supplied by a Socratic AI mentor protected by regex "
        "redaction filters that strip credentials and block direct CLI answers. Scoring combines exponential time "
        "decay with AST Levenshtein anti-drift penalties, while a read-only local FastAPI service renders a live "
        "SVG topology dashboard. Validated across 129 automated tests (100% pass rate), t2t bridges theoretical "
        "redistribution principles with verifiable operational mastery."
    )
    add_body_p(
        "CCNP Enterprise, Route Redistribution, EIGRP, OSPF, Administrative Distance, Route Tagging, Abstract Syntax "
        "Tree, Deterministic Verification, Socratic Tutoring, Network Simulation, FastAPI.",
        bold_prefix="Keywords: ",
        italic=True,
    )

    # Acknowledgement
    s_ack = doc.add_section()
    set_section_margins(s_ack)
    style_header_footer(s_ack, "Acknowledgement", is_roman=True)

    add_chapter_heading("ACKNOWLEDGEMENT")
    add_body_p(
        f'I express my sincere gratitude to everyone who supported the design, implementation, and validation of '
        f'"{PROJECT_TITLE}".'
    )
    add_body_p(
        "I am deeply thankful to my internal supervisor, Prof. Harshul Yagnik, Department of Computer Science & "
        "Engineering, for his technical mentorship, constructive reviews, and continuous encouragement throughout "
        "the 14-week development cycle. His insights into routing protocol behavior and verification engineering "
        "directly shaped the AST parser and deterministic oracle architecture."
    )
    add_body_p(
        "I extend my heartfelt appreciation to Dr. Amit Thakkar, Head of the Department of Computer Science & "
        "Engineering, CSPIT, CHARUSAT, for providing laboratory infrastructure and fostering a rigorous engineering "
        "environment. I also thank the faculty, lab assistants, and peers who assisted with scenario qualification, "
        "and my family and friends for their unwavering support."
    )

    # Table of Content
    s_toc = doc.add_section()
    set_section_margins(s_toc)
    style_header_footer(s_toc, "Table of Content", is_roman=True)

    add_chapter_heading("TABLE OF CONTENT")
    toc_rows = [
        ([sec, title, page_map.get(key, "")], is_bold)
        for sec, title, key, is_bold in TOC_SPEC
    ]
    add_table_data(
        ["Section", "Title / Topic", "Page No."],
        toc_rows,
        caption_num_name=None,
        col_widths=[1.0, 4.2, 0.8],
        font_size=9.2,
        center_cols=(0, 2),
    )

    # List of Figures
    s_lof = doc.add_section()
    set_section_margins(s_lof)
    style_header_footer(s_lof, "List of Figures", is_roman=True)

    add_chapter_heading("LIST OF FIGURES")
    lof_rows = [[f_no, f_title, page_map.get(f_key, "")] for f_no, f_title, f_key in FIGURES_SPEC]
    add_table_data(
        ["Figure No.", "Figure Title / Caption", "Page No."],
        lof_rows,
        caption_num_name=None,
        col_widths=[1.0, 4.2, 0.8],
        font_size=9.5,
        center_cols=(0, 2),
    )

    # List of Tables
    s_lot = doc.add_section()
    set_section_margins(s_lot)
    style_header_footer(s_lot, "List of Tables", is_roman=True)

    add_chapter_heading("LIST OF TABLES")
    lot_rows = [[t_no, t_title, page_map.get(t_key, "")] for t_no, t_title, t_key in TABLES_SPEC]
    add_table_data(
        ["Table No.", "Table Title / Caption", "Page No."],
        lot_rows,
        caption_num_name=None,
        col_widths=[1.0, 4.2, 0.8],
        font_size=9.5,
        center_cols=(0, 2),
    )

    # ------------------------------------------------------------------
    # CHAPTER 1: INTRODUCTION
    # ------------------------------------------------------------------
    s_ch1 = doc.add_section()
    set_section_margins(s_ch1)
    style_header_footer(s_ch1, "Chapter 1: Introduction", is_roman=False, start_num=1)

    add_chapter_heading("CHAPTER 1: INTRODUCTION")

    add_section_heading("1.1 Project Summary")
    add_body_p(
        "Ticket-to-Topology (t2t) is a specialized network engineering simulator, static configuration auditor, and "
        "pedagogical troubleshooting platform built to analyze and verify multi-point mutual route redistribution "
        "between Enhanced Interior Gateway Routing Protocol (EIGRP AS 100) and Open Shortest Path First (OSPF "
        "Process 1 Area 0). Enterprises frequently bridge disparate IGP domains during mergers or core migrations, "
        "yet dual-ASBR mutual redistribution remains highly error-prone because composite vector metrics and "
        "link-state costs do not translate natively and Administrative Distance (AD) defaults conflict."
    )
    add_body_p(
        "Ticket-to-Topology addresses this challenge through a dual-mode CLI and web platform: (1) a Static "
        "Redistribution Audit Engine that parses Cisco IOS-XE configurations into an Abstract Syntax Tree (AST) "
        "to detect policy flaws prior to deployment, and (2) an interactive Troubleshooting Simulator that injects "
        "calibrated faults, grades fixes with deterministic invariant checks and anti-drift scoring, and guides "
        "learners via a guarded Socratic AI mentor."
    )

    add_section_heading("1.2 Purpose")
    add_body_p(
        "This project closes the operational gap between theoretical routing study and hands-on incident response "
        "for CCNP Enterprise candidates (ENCOR 350-401 and ENARSI 300-410) and network engineers. Static study "
        "guides and unguided emulators fail to explain why route feedback or suboptimal forwarding occurs, while "
        "production teams lack lightweight AST-aware offline linters to catch redistribution defects before change "
        "windows. t2t provides both a reproducible training sandbox and an automated pre-deployment audit utility."
    )

    add_section_heading("1.3 Objective")
    add_bullet_p("Parse Cisco IOS-XE running configs into a hierarchical AST covering EIGRP, OSPF, route-maps, prefix-lists, and AD tuning.", bold_prefix="Deterministic AST Parsing: ")
    add_bullet_p("Enforce seven static audit rules (A1–A7) detecting missing seed metrics, unguarded mutual redistribution, omitted route tags, and AD inversion.", bold_prefix="Static Configuration Linting: ")
    add_bullet_p("Inject seven parameterized YAML fault scenarios (T1–T7) over live Netmiko SSH or deterministic offline mock replay fixtures.", bold_prefix="Fault Injection Framework: ")
    add_bullet_p("Validate control-plane convergence (protocol, next-hop, metrics) via an algorithmic Verification Oracle with zero AI dependency.", bold_prefix="Deterministic Verification Oracle: ")
    add_bullet_p("Deliver Socratic hints via Ollama/LLM APIs filtered through regex guards that redact secrets and prohibit direct CLI answers.", bold_prefix="Pedagogical Socratic Mentor: ")
    add_bullet_p("Combine exponential time decay with AST Levenshtein distance penalties to discourage unstructured trial-and-error drift.", bold_prefix="Anti-Drift Scoring Engine: ")
    add_bullet_p("Serve a read-only local FastAPI dashboard displaying real-time green/amber/red SVG topology health and audit telemetry.", bold_prefix="Lightweight Telemetry & Web UI: ")

    add_section_heading("1.4 Scope")
    add_subsection_heading("1.4.1 In-Scope Capabilities")
    add_bullet_p("Four-router dual-boundary topology: R1 (Branch), R2/R3 (Primary/Secondary ASBRs), and R4 (HQ Core) running EIGRP AS 100 and OSPF Area 0.")
    add_bullet_p("Hierarchical Cisco IOS-XE AST parsing, seven static audit rules (A1–A7), and seven fault scenarios (T1–T7).")
    add_bullet_p("Netmiko SSH orchestration, 100% offline deterministic replay fixtures, SQLite WAL persistence, and read-only FastAPI SVG visualization.")

    add_subsection_heading("1.4.2 Out-of-Scope Capabilities")
    add_bullet_p("MP-BGP EVPN/VXLAN overlays, IPv6 routing (OSPFv3/EIGRPv6), and non-Cisco NOS dialects (Junos, Arista EOS).")
    add_bullet_p("Browser-initiated configuration mutations (web endpoints are strictly GET-only and localhost-bound by default).")

    add_section_heading("1.5 Technology and Literature Review")
    add_body_p(
        "The routing model adheres to IETF RFC 2328 (OSPFv2), RFC 7868 (EIGRP), and Cisco CCNP Enterprise ENCOR/ENARSI "
        "design theory (Edelman et al., 2023). Because EIGRP assigns AD 90 to internal routes and AD 170 to external "
        "routes while OSPF uses a uniform AD of 110, redistributing EIGRP routes into OSPF at one ASBR causes the peer "
        "ASBR to prefer the OSPF path (AD 110) over EIGRP external (AD 170)—an Administrative Distance Inversion that "
        "drives suboptimal routing and circular feedback loops unless mitigated with route tagging and distance tuning."
    )
    add_body_p(
        "Existing analysis tools such as Batfish (Fogel et al., NSDI 2015) and Cisco pyATS/Genie excel at data-plane "
        "modeling or device parsing but require heavy infrastructure and offer no interactive scoring or pedagogical "
        "scaffolding. Meanwhile, unconstrained LLMs tend to dump full CLI answers rather than teach (Tack & Piech, "
        "2022). Ticket-to-Topology resolves these gaps using the streamlined Python stack summarized in Table 1.1."
    )

    add_table_data(
        ["Category", "Tool / Technology", "Specific Purpose in Ticket-to-Topology"],
        [
            ["Core Language", "Python 3.12+ (Typed)", "Domain modeling, IOS-XE AST parsing, strict static typing via mypy"],
            ["CLI Interface", "Typer & Rich", "Interactive terminal commands, progress spinners, color telemetry tables"],
            ["Network Driver", "Netmiko (Paramiko)", "Live SSH device sessions, privileged exec, bounded config pushes"],
            ["Web Framework", "FastAPI & Uvicorn", "Read-only GET endpoints, token auth, interactive SVG topology UI"],
            ["Database", "SQLite 3 (WAL Mode)", "ACID session persistence, attempt history, verification and audit logs"],
            ["AI Integration", "LiteLLM / Ollama", "Socratic tutoring with local/remote models and regex redaction guards"],
            ["Quality & Testing", "Ruff, Mypy, Pytest", "PEP 8 linting, type verification across 52 files, 129 automated tests"],
            ["Lab Target", "Cisco IOS-XE (CSR1000v)", "Reference 4-router dual-ASBR mutual redistribution testbed"],
        ],
        "Table 1.1 Tools and Technologies Used",
        [1.25, 1.65, 3.1],
    )

    # ------------------------------------------------------------------
    # CHAPTER 2: PROJECT MANAGEMENT
    # ------------------------------------------------------------------
    s_ch2 = doc.add_section()
    set_section_margins(s_ch2)
    style_header_footer(s_ch2, "Chapter 2: Project Management", is_roman=False)

    add_chapter_heading("CHAPTER 2: PROJECT MANAGEMENT")

    add_section_heading("2.1 Project Planning")
    add_body_p(
        "Development spanned a 14-week academic schedule organized into ten strict engineering phase gates plus "
        "lab qualification and final documentation (Table 2.1). Decoupled module boundaries enabled independent unit "
        "testing and continuous regression verification throughout the semester."
    )

    add_table_data(
        ["Phases", "Key Activities & Milestones", "Weeks", "Primary Deliverables"],
        [
            ["Phases 1–2", "Topology baseline design, inventory schema, IOS-XE show-run parser & AST", "W1–W3", "lab/inventory.yaml, t2t.parsers, U1–U2 tests"],
            ["Phase 3", "Deterministic Static Redistribution Audit Engine (Rules A1 through A7)", "W3–W4", "t2t.audit (engine, rules), U3 tests"],
            ["Phases 4–5", "DeviceSession abstraction, Netmiko SSH, mock replay fixtures, Faults T1–T7", "W4–W7", "t2t.devices, t2t.faults YAML, U4–U5 tests"],
            ["Phases 6–7", "Decoupled Verification Oracle (no-AI), time-decay & AST anti-drift scoring", "W7–W9", "t2t.verify, t2t.session.scoring, U6–U7 tests"],
            ["Phase 8", "Socratic AI Mentor integration, prompt guardrails & regex secret redactor", "W9–W10", "t2t.ai (mentor, redactor), U8 tests"],
            ["Phases 9–10", "Typer CLI, offline demo, Docker build, read-only FastAPI & SVG dashboard", "W10–W12", "t2t.cli, Dockerfile, t2t.web, U9–U10 tests"],
            ["QA & Report", "Lab qualification runs, 129-test regression suite, ruff/mypy, final report", "W12–W14", "129 passing tests, final project report"],
        ],
        "Table 2.1 Project Planning Breakdown (14-Week Schedule)",
        [0.95, 2.55, 0.75, 1.75],
    )

    add_subsection_heading("2.1.1 Project Development Approach and Justification")
    add_body_p(
        "The project adopted Test-Driven Development (TDD) inside an iterative Agile workflow governed by AGENTS.md "
        "phase gates (U1.1–U10.3). Every component required failing unit tests before implementation. Because routing "
        "invariants are mathematically unforgiving—a single misparsed route-map tag or wrong AD check would corrupt "
        "grading—TDD caught grammar edge cases and replay anomalies early while preserving zero regressions."
    )

    add_subsection_heading("2.1.2 Project Effort, Time, and Cost Estimation")
    add_body_p(
        "Effort was modeled via COCOMO II for semi-detached software across ~5,280 SLOC (52 typed Python modules): "
        "Effort = 2.94 × (5.2)^1.09 × 1.05 = 18.4 Person-Months (nominal TDEV = 8.9 months, compressed into 14 "
        "intensive weeks through modular tooling and offline fixtures). Table 2.2 summarizes resource economics."
    )

    add_table_data(
        ["Metric Category", "Estimated Parameter", "Actual Value / Justification"],
        [
            ["Source Volume (SLOC)", "5,000–6,000 SLOC", "5,280 typed Python SLOC (excluding fixtures)"],
            ["System Complexity", "High (AST & Protocol State)", "Hierarchical CLI grammar + FSM + invariant oracle"],
            ["Hardware / Lab Cost", "$0 (Virtual) / $1,200 (Physical)", "$0 direct hardware spend via offline mock replay"],
            ["LLM & Software Cost", "Open-source academic stack", "$0 licensing cost (Python, FastAPI, SQLite, Ollama)"],
        ],
        "Table 2.2 COCOMO-II Effort & Resource Estimation",
        [1.55, 1.85, 2.6],
    )

    add_subsection_heading("2.1.3 Roles and Responsibilities")
    add_table_data(
        ["Engineering Role", "Primary Responsibilities", "Associated Packages"],
        [
            ["System Architect", "FSM design, SQLite schema, phase-gate governance", "t2t.session, docs/BUILD_GUIDE.md"],
            ["AST & Audit Engineer", "Cisco IOS-XE parser, AST models, static rules A1–A7", "t2t.parsers, t2t.audit"],
            ["Network & Fault Dev", "Netmiko SSH driver, mock replay harness, faults T1–T7", "t2t.devices, t2t.faults"],
            ["Verification & Scoring", "Control-plane invariant oracle, time-decay & anti-drift math", "t2t.verify, t2t.session.scoring"],
            ["AI, Web & Packaging", "Socratic mentor, regex redactor, FastAPI SVG UI, Docker", "t2t.ai, t2t.web, t2t.cli"],
        ],
        "Table 2.3 Roles and Module Ownership",
        [1.45, 2.55, 2.0],
    )

    add_subsection_heading("2.1.4 Group Dependencies")
    add_body_p(
        "Strict unidirectional layering eliminates circular coupling: `t2t.parsers` feeds `t2t.audit` and anti-drift "
        "scoring; `t2t.devices` isolates SSH/replay transport from `t2t.faults` and `t2t.verify`. Per AGENTS.md "
        "Rule 3, the Verification Oracle, Fault Catalog, and Scoring Engine have zero imports from `t2t.ai`, ensuring "
        "deterministic pass/fail decisions independent of language models."
    )

    add_section_heading("2.2 Project Scheduling")
    add_body_p(
        "Figure 2.1 maps all development phases across Weeks 1–14, highlighting the critical path through DeviceSession "
        "abstraction (Phase 4) and the Verification Oracle (Phase 6)."
    )
    add_figure_image("fig_2_1_gantt_chart.png", "Fig 2.1 Gantt Chart (14-Week Development Schedule)", width_in=5.1)

    # ------------------------------------------------------------------
    # CHAPTER 3: SYSTEM REQUIREMENTS STUDY
    # ------------------------------------------------------------------
    s_ch3 = doc.add_section()
    set_section_margins(s_ch3)
    style_header_footer(s_ch3, "Chapter 3: System Requirements Study", is_roman=False)

    add_chapter_heading("CHAPTER 3: SYSTEM REQUIREMENTS STUDY")

    add_section_heading("3.1 User Characteristics")
    add_body_p(
        "Ticket-to-Topology serves three distinct user groups—certification learners, enterprise auditors, and lab "
        "instructors—whose profiles and workflows are detailed in Table 3.1 and illustrated in Figure 3.1."
    )

    add_table_data(
        ["User Role", "Technical Background", "Primary System Interactions"],
        [
            ["CCNP Candidate / Student", "CCNA-level IP routing; mastering EIGRP/OSPF redistribution", "Starts tickets, audits routes, pushes fixes, queries Socratic hints, reviews scores"],
            ["Network Auditor / Engineer", "Enterprise routing specialist auditing production configs", "Runs offline static audits (A1–A7), inspects JSON compliance & route-tag findings"],
            ["Lab Instructor / Admin", "Curriculum designer overseeing physical or virtual labs", "Maintains YAML fault catalogs, sets baseline checks, tracks progress via Web UI"],
        ],
        "Table 3.1 User Characteristics Matrix",
        [1.55, 1.95, 2.5],
    )

    add_figure_image("fig_3_1_use_case.png", "Fig 3.1 System Use Case Diagram", width_in=5.0)

    add_section_heading("3.2 Hardware and Software Requirements")
    add_body_p(
        "The platform runs offline on standard student laptops using packaged replay fixtures or connects over SSH "
        "to physical/virtual Cisco IOS-XE testbeds (Table 3.2)."
    )

    add_table_data(
        ["System Component", "Minimum Development Spec (Offline)", "Production / Live Lab Spec"],
        [
            ["Processor (CPU)", "Intel Core i3 / Ryzen 3 (2 cores)", "Intel Core i7 / Ryzen 7 (4+ cores, AVX2)"],
            ["Memory (RAM)", "4 GB RAM (Replay Mock Mode)", "16 GB RAM (hosting 4x CSR1000v instances)"],
            ["Storage Space", "500 MB free disk space", "20 GB free space (virtual router images & logs)"],
            ["Operating System", "Windows 10/11, Ubuntu 22.04, or macOS", "Linux Server (Ubuntu 22.04 LTS / Debian 12)"],
            ["Python Runtime", "Python 3.12+ (64-bit, .venv)", "Python 3.12+ or containerized Docker runtime"],
            ["Target Routers", "Packaged IOS-XE Replay Fixtures", "4x Cisco IOS-XE (CSR1000v / C8000v / Cat8300)"],
            ["Network & Browser", "127.0.0.1 loopback; modern SVG browser", "Isolated OOB SSH management plane + browser"],
        ],
        "Table 3.2 Hardware & Software Requirements Specification",
        [1.45, 2.2, 2.35],
    )

    add_section_heading("3.3 Assumptions and Dependencies")
    add_body_p(
        "Operational safety and deterministic grading rely on five architectural preconditions captured in Table 3.3."
    )

    add_table_data(
        ["ID", "Technical Assumption / Dependency", "Impact if Violated & Mitigation"],
        [
            ["DEP-1", "Cisco IOS-XE CLI prompts match standard hostname# format", "Prompt mismatch stalls SSH; mitigated via configurable prompt regex"],
            ["DEP-2", "All router mutations pass strictly via DeviceSession.push_config", "Bypassing breaks audit/drift logs; enforced as AGENTS.md Rule 4"],
            ["DEP-3", "Replay tests use real captured router outputs, not synthetic text", "Synthetic fixtures cause false passes; immutable fixtures enforced (Rule 5)"],
            ["DEP-4", "Out-of-Band (OOB) management plane is isolated from data plane", "Route churn would sever SSH; dedicated Gig0/0 OOB subnets isolate control"],
            ["DEP-5", "FastAPI dashboard stays read-only and bound to 127.0.0.1", "Exposed writes risk tampering; 0.0.0.0 refused without flag + bearer token"],
        ],
        "Table 3.3 Assumptions and Technical Dependencies",
        [0.65, 2.55, 2.8],
    )

    # ------------------------------------------------------------------
    # CHAPTER 4: SYSTEM ANALYSIS
    # ------------------------------------------------------------------
    s_ch4 = doc.add_section()
    set_section_margins(s_ch4)
    style_header_footer(s_ch4, "Chapter 4: System Analysis", is_roman=False)

    add_chapter_heading("CHAPTER 4: SYSTEM ANALYSIS")

    add_section_heading("4.1 Study of Current System")
    add_body_p(
        "Conventional route redistribution training depends on physical router racks, graphical emulators (GNS3, "
        "EVE-NG, Cisco CML), and static PDF workbooks. While emulators replicate forwarding behavior, they lack "
        "automated invariant checking, structured scoring, and targeted guidance. In production operations, engineers "
        "still audit redistribution manually or rely on brittle grep scripts that ignore IOS-XE hierarchy."
    )

    add_section_heading("4.2 Problem and Weaknesses of Current System")
    add_bullet_p("Physical hardware racks exceed $5,000, while 4-router virtual labs demand 16+ GB RAM unavailable on basic student laptops.", bold_prefix="High Infrastructure Cost: ")
    add_bullet_p("Emulators offer no control-plane pass/fail oracle, leaving learners stuck on silent suboptimal routes or loops.", bold_prefix="No Automated Verification: ")
    add_bullet_p("Flat regex scripts cannot bind indented commands (e.g., default-metric or match tag) to their parent router/route-map block.", bold_prefix="No AST Semantics: ")
    add_bullet_p("Unregulated public LLMs immediately dump complete CLI configs, undermining conceptual mastery.", bold_prefix="AI Answer-Dumping: ")

    add_table_data(
        ["Feature Dimension", "Physical / GNS3 Labs", "Static Workbooks", "Ticket-to-Topology (t2t)"],
        [
            ["Hardware Overhead", "High (4+ routers)", "None (PDF/paper)", "Zero (Offline Replay Engine)"],
            ["Verification Engine", "Manual ping/trace", "Self-check only", "Deterministic Control-Plane Oracle"],
            ["Config Parsing", "Visual review", "None", "Hierarchical IOS-XE AST Parser"],
            ["Static Audit Rules", "None", "None", "7 Rules (A1–A7: seeds, tags, loops, AD)"],
            ["Pedagogical Hints", "Instructor-bound", "Static keys", "Socratic AI Mentor + Regex Redactor"],
            ["Scoring Model", "Binary pass/fail", "None", "Time-Decay + AST Levenshtein Anti-Drift"],
            ["Telemetry UI", "Packet captures", "Static diagrams", "Read-Only Dynamic SVG Web Dashboard"],
        ],
        "Table 4.1 Comparative Analysis: Existing Approaches vs Ticket-to-Topology (t2t)",
        [1.45, 1.35, 1.25, 1.95],
    )

    add_figure_image("fig_4_1_architecture.png", "Fig 4.1 Ticket-to-Topology (t2t) Multi-Tier System Architecture", width_in=5.1)

    add_section_heading("4.3 Requirements of New System")
    add_subsection_heading("4.3.1 Functional Requirements")
    add_table_data(
        ["ID", "Functional Requirement Statement", "Category", "Priority"],
        [
            ["FR1", "Parse Cisco IOS-XE 'show run' into an AST of EIGRP, OSPF, route-maps, and prefix-lists.", "Parsing", "Critical"],
            ["FR2", "Evaluate 7 static audit rules (A1–A7) for missing seeds, loops, tags, and AD inversion.", "Audit", "Critical"],
            ["FR3", "Load parameterized fault scenarios (T1–T7) from validated YAML catalog definitions.", "Faults", "High"],
            ["FR4", "Inject faults into live routers via Netmiko SSH or offline mock replay fixtures.", "Devices", "Critical"],
            ["FR5", "Apply candidate fixes strictly via DeviceSession.push_config with read-only guard.", "Devices", "Critical"],
            ["FR6", "Verify routing table invariants (protocol, next-hop, metric) with zero AI dependency.", "Verify", "Critical"],
            ["FR7", "Compute candidate scores using exponential time decay and AST anti-drift penalties.", "Scoring", "High"],
            ["FR8", "Persist sessions, attempts, verification logs, and scores in SQLite WAL storage.", "Storage", "High"],
            ["FR9", "Provide a Socratic AI mentor that redacts secrets and blocks direct CLI syntax.", "AI Mentor", "Medium"],
            ["FR10", "Expose a Typer/Rich CLI with colored check tables, spinners, and offline demo mode.", "CLI", "High"],
            ["FR11", "Run a GET-only FastAPI server bound to 127.0.0.1 with remote-bind token guard.", "Web UI", "High"],
            ["FR12", "Render an interactive SVG topology showing real-time link health and ticket history.", "Web UI", "Medium"],
        ],
        "Table 4.2 Functional Requirements (FR1 to FR12)",
        [0.6, 3.65, 0.9, 0.85],
    )

    add_subsection_heading("4.3.2 Non-Functional Requirements")
    add_table_data(
        ["Attribute", "Technical Non-Functional Specification", "Verification Method"],
        [
            ["NFR1: Performance", "Offline replay verification and static audits complete in < 2.0 seconds.", "Pytest timing (129 tests in 10.13s)"],
            ["NFR2: Determinism", "Repeated verification runs yield identical PASS/FAIL verdicts.", "t2t qualify --fault T3 --runs 3"],
            ["NFR3: Portability", "Consistent execution on Windows, Linux, macOS, and Docker containers.", "Docker build & cross-platform tests"],
            ["NFR4: Security", "Zero hardcoded secrets; credentials resolved solely from environment vars.", "Static scan & regex redactor tests"],
            ["NFR5: Safety", "Web API enforces GET-only routes and refuses unauthenticated 0.0.0.0 bind.", "FastAPI contract tests (U10.2–U10.3)"],
            ["NFR6: Maintainability", "Zero time.sleep calls; all timers use injectable Clock abstraction.", "Ruff lint & AGENTS.md Rule 10"],
            ["NFR7: Code Quality", "100% PEP 484 type compliance across all 52 Python source modules.", "Mypy strict check (0 errors)"],
            ["NFR8: Reliability", "Crash-resilient transactional storage with foreign-key enforcement.", "SQLite PRAGMA journal_mode=WAL"],
        ],
        "Table 4.3 Non-Functional Requirements (NFR1 to NFR8)",
        [1.4, 2.7, 1.9],
    )

    add_section_heading("4.4 Feasibility Study")
    add_subsection_heading("4.4.1 Organizational Objectives Contribution")
    add_body_p(
        "Ticket-to-Topology directly advances CHARUSAT's computer networking curriculum by giving B.Tech students a "
        "reproducible, objective examination platform for CCNP ENCOR/ENARSI skills. In enterprise IT operations, "
        "its static audit engine reduces production outage risk by catching redistribution flaws before cutovers."
    )

    add_subsection_heading("4.4.2 Technical and Schedule Feasibility")
    add_body_p(
        "The entire platform leverages mature open-source Python technologies (Typer, FastAPI, Netmiko, SQLite) with "
        "zero licensing costs. Packaging captured IOS-XE replay fixtures eliminated hardware procurement bottlenecks, "
        "enabling all 10 engineering phase gates to complete cleanly within the 14-week semester schedule."
    )

    add_subsection_heading("4.4.3 System Integration Feasibility")
    add_body_p(
        "t2t integrates seamlessly into existing NetOps workflows: Netmiko speaks standard SSHv2 across Cisco IOS/IOS-XE "
        "fleets, the Static Audit Engine emits JSON Schema reports compatible with CI/CD pipelines (GitHub Actions, "
        "GitLab CI), and the FastAPI endpoints (/api/status, /api/session, /api/history, /api/audit/latest) expose "
        "clean read-only telemetry for monitoring dashboards."
    )

    add_section_heading("4.5 Activity / Process in New System")
    add_body_p(
        "Figure 4.2 depicts the eight-stage operational workflow: ticket generation, fault injection, candidate "
        "discovery and static auditing, config submission, deterministic invariant verification, and either "
        "anti-drift scoring (on pass) or Socratic guided feedback (on fail)."
    )
    add_figure_image("fig_4_2_activity_flow.png", "Fig 4.2 End-to-End Troubleshooting Activity Process Flow", width_in=5.0)

    add_section_heading("4.6 Features of New System")
    add_bullet_p("Unites an interactive CLI troubleshooting lab with an offline production-safe Static Redistribution Auditor.", bold_prefix="Dual-Mode Operation: ")
    add_bullet_p("Penalizes extraneous configuration lines via AST Levenshtein distance against canonical solutions.", bold_prefix="AST Anti-Drift Scoring: ")
    add_bullet_p("Verifies protocol, next-hop, and metric convergence strictly algorithmically—never delegating grading to LLMs.", bold_prefix="Zero-AI Verification Oracle: ")
    add_bullet_p("Combines Socratic prompt constraints with regex sanitization to block credentials and direct CLI answers.", bold_prefix="Guarded Socratic AI Mentor: ")
    add_bullet_p("Renders live green/amber/red SVG topology health over strictly read-only GET endpoints.", bold_prefix="Read-Only SVG Dashboard: ")

    add_section_heading("4.7 Use Case Diagram & Descriptions")
    add_body_p(
        "Core actor interactions (Figure 3.1) are formally specified in Table 4.4."
    )

    add_table_data(
        ["ID", "Use Case", "Primary Actor", "Pre-condition", "Main Success Scenario"],
        [
            ["UC-01", "Initialize Ticket", "Candidate", "FSM IDLE; valid YAML catalog", "1. Run 't2t new-ticket'. 2. Inject fault (e.g., T3) into R2/R3. 3. Transition to ACTIVE and start timer."],
            ["UC-02", "Run Static Audit", "Auditor / Student", "Running config available", "1. Run 't2t audit'. 2. Parse IOS-XE AST. 3. Evaluate Rules A1–A7 and display severity findings."],
            ["UC-03", "Submit Fix", "Candidate", "Session ACTIVE", "1. Run 't2t submit'. 2. Push remediation via DeviceSession. 3. Oracle checks invariants; record score."],
            ["UC-04", "Query Hint", "Candidate", "Active failed check", "1. Run 't2t hint'. 2. Redact sensitive tokens. 3. Return Socratic question without CLI commands."],
            ["UC-05", "View Telemetry", "Observer / Student", "FastAPI server running", "1. Open 127.0.0.1:8000. 2. Poll GET /api/* endpoints. 3. Render SVG link colors and audit history."],
        ],
        "Table 4.4 Use Case Specifications",
        [0.65, 1.1, 1.05, 1.25, 1.95],
    )

    add_section_heading("4.8 Class Diagram")
    add_body_p(
        "Figure 4.3 presents the object-oriented class hierarchy, and Table 4.5 defines key attributes and method contracts."
    )
    add_figure_image("fig_4_3_class_diagram.png", "Fig 4.3 High-Level Unified Class Diagram (OOP Design)", width_in=5.0)

    add_table_data(
        ["Class Name", "Key Attributes", "Public Method Contract", "Collaborators"],
        [
            ["DeviceSession", "host, read_only, _protocol", "send_command(cmd), push_config(lines)", "NetmikoDevice, MockDevice"],
            ["RedistributionAST", "eigrp_instances, ospf_processes, route_maps", "get_sources(proto), find_metric_issues()", "CiscoIOSXEParser, AuditEngine"],
            ["AuditEngine", "rules, ast", "evaluate_all(), check_rule(rule_id)", "RedistributionAST, AuditReport"],
            ["VerificationOracle", "baseline_checks, fault_checks", "verify_topology(devices), evaluate_invariants()", "DeviceSession, SessionFSM"],
            ["SessionFSM", "state, clock, db", "transition_to(state), score_attempt(diff, t)", "Clock, SQLiteManager"],
        ],
        "Table 4.5 Core Object Classes and Method Contracts",
        [1.25, 1.75, 1.7, 1.3],
    )

    add_section_heading("4.9 Sequence Diagram")
    add_body_p(
        "Figure 4.4 traces chronological message passing from ticket initialization and fault injection through "
        "candidate submission, deterministic invariant verification, and Socratic hint delivery."
    )
    add_figure_image("fig_4_4_sequence_diagram.png", "Fig 4.4 Sequence Diagram: Verification & Socratic Guidance Lifecycle", width_in=5.0)

    # ------------------------------------------------------------------
    # CHAPTER 5: SYSTEM DESIGN (Section 5.1.1 REMOVED as requested)
    # ------------------------------------------------------------------
    s_ch5 = doc.add_section()
    set_section_margins(s_ch5)
    style_header_footer(s_ch5, "Chapter 5: System Design", is_roman=False)

    add_chapter_heading("CHAPTER 5: SYSTEM DESIGN")

    add_section_heading("5.1 System Application Design")
    add_body_p(
        "The application architecture revolves around four tightly coordinated domain engines operating over the "
        "dual-boundary reference topology shown in Figure 5.1 (R1 Branch in EIGRP AS 100, R2 and R3 acting as "
        "redundant ASBRs interconnected across 10.1.23.0/24, and R4 HQ in OSPF Area 0)."
    )
    add_body_p(
        "First, the Cisco IOS-XE Hierarchical AST Parser tracks indentation levels to bind sub-commands—such as "
        "'redistribute ospf 1 metric ...', 'distance ospf external 171', and 'match/set tag'—to their parent "
        "'router eigrp', 'router ospf', 'route-map', and 'ip prefix-list' blocks rather than matching flat text. "
        "Second, the Static Audit Engine inspects the AST against seven deterministic rules (A1–A7), flagging "
        "missing EIGRP/OSPF seed metrics (A1–A2), mutual redistribution lacking route-tag loop filters (A3–A4), "
        "AD inversion where OSPF AD 110 overrides EIGRP external AD 170 (A5), and incomplete prefix filtering (A6–A7). "
        "Third, the Verification Oracle queries 'show ip route <prefix>' across target devices to assert exact "
        "protocol, next-hop, and metric invariants with zero AI involvement. Finally, the Anti-Drift Scoring Engine "
        "combines normalized AST Levenshtein distance (tolerating minor cosmetic differences while penalizing "
        "extraneous churn) with an exponential time-decay multiplier to produce a normalized 0–100 score."
    )
    add_figure_image("fig_5_1_redistribution_topology.png", "Fig 5.1 CCNP Enterprise Dual-Point Mutual Route Redistribution Topology", width_in=5.1)

    add_section_heading("5.2 Input / Output and Interface Design")
    add_subsection_heading("5.2.1 Samples of Forms, Reports, and Interface")
    add_body_p(
        "Users interact via two complementary interfaces: a Rich-formatted Typer CLI ('t2t new-ticket', 't2t audit', "
        "'t2t status', 't2t submit', 't2t hint', 't2t demo') that displays color-coded invariant verification tables "
        "and JSON Schema audit reports, and a read-only FastAPI web interface (Figure 5.2). The browser dashboard "
        "polls GET-only endpoints (/api/status, /api/session, /api/history, /api/audit/latest) to dynamically paint "
        "SVG topology links green (verified), amber (warning/suboptimal), or red (invariant failure)."
    )
    add_figure_image("fig_5_2_web_dashboard.png", "Fig 5.2 FastAPI Lightweight Web Interface Mockup with Interactive SVG Canvas", width_in=5.1)

    add_subsection_heading("5.2.2 State Diagram")
    add_body_p(
        "Each troubleshooting session is governed by the Finite State Machine (FSM) in Figure 5.3. Starting from "
        "IDLE, 't2t new-ticket' injects the fault and enters ACTIVE. Executing 't2t submit' moves to EVALUATING; "
        "passing all checks transitions to RESOLVED with score recording, whereas failed checks return to ACTIVE "
        "with diagnostic feedback until either solved or transitioned to EXPIRED upon timeout."
    )
    add_figure_image("fig_5_3_state_machine.png", "Fig 5.3 Finite State Machine (FSM) Lifecycle Diagram", width_in=5.0)

    add_section_heading("5.3 System Structural Design & Database Schema")
    add_body_p(
        "Session state, submission diffs, verification outcomes, and awarded scores are stored in SQLite 3 enabled "
        "with Write-Ahead Logging (WAL) and enforced foreign keys for safe concurrent CLI/Web reads (Figure 5.4 and "
        "Table 5.1)."
    )
    add_figure_image("fig_5_4_er_diagram.png", "Fig 5.4 SQLite WAL Session Store Entity-Relationship (ER) Schema", width_in=5.0)

    add_table_data(
        ["Table Name", "Key Columns & Types", "Constraints & Keys", "Role in System"],
        [
            ["sessions", "session_id (TEXT), fault_id (TEXT), status (TEXT), started_at (TIMESTAMP)", "PK(session_id); CHECK status IN (ACTIVE, RESOLVED, EXPIRED)", "Tracks active & historical FSM lifecycle"],
            ["attempts", "attempt_id (INT), session_id (TEXT), submitted_config (TEXT), ast_diff_penalty (REAL)", "PK(attempt_id); FK(session_id) -> sessions", "Stores candidate configs & AST drift penalties"],
            ["verification_logs", "log_id (INT), session_id (TEXT), check_id (TEXT), status (TEXT), observed_value (TEXT)", "PK(log_id); FK(session_id); CHECK status IN (PASS, FAIL)", "Records per-invariant oracle verdicts"],
            ["scores", "score_id (INT), session_id (TEXT), final_score (REAL), time_decay (REAL)", "PK(score_id); UNIQUE FK(session_id) -> sessions", "Stores final 0–100 normalized score"],
        ],
        "Table 5.1 Database Schema Dictionary (SQLite WAL Mode)",
        [1.1, 2.0, 1.55, 1.35],
    )

    # ------------------------------------------------------------------
    # CHAPTER 6: IMPLEMENTATION PLANNING
    # ------------------------------------------------------------------
    s_ch6 = doc.add_section()
    set_section_margins(s_ch6)
    style_header_footer(s_ch6, "Chapter 6: Implementation Planning", is_roman=False)

    add_chapter_heading("CHAPTER 6: IMPLEMENTATION PLANNING")

    add_section_heading("6.1 Implementation Environment")
    add_body_p(
        "Ticket-to-Topology was built in an isolated Python 3.12 virtual environment across Windows 11 and Linux, "
        "packaged via standard pyproject.toml metadata and containerized in a slim Docker image. Transport details "
        "are encapsulated behind a DeviceProtocol interface so live Netmiko SSH and offline mock replay share identical "
        "execution paths."
    )

    add_section_heading("6.2 Modules Specification")
    add_table_data(
        ["Package", "Key Source Files", "Architectural Scope & Responsibilities"],
        [
            ["t2t.parsers", "cisco_iosxe.py, ast.py", "Parses IOS-XE running configs into structured EIGRP/OSPF/route-map ASTs"],
            ["t2t.audit", "engine.py, rules.py, models.py", "Static Redistribution Audit Engine evaluating deterministic rules A1–A7"],
            ["t2t.devices", "session.py, netmiko_device.py, mock.py", "Device abstraction handling SSH sessions, replay fixtures, and config pushes"],
            ["t2t.faults", "catalog.py, loader.py, injector.py", "YAML fault catalog validation and controlled injection for scenarios T1–T7"],
            ["t2t.verify", "oracle.py, checks.py, invariants.py", "Zero-AI Verification Oracle asserting routing protocol, next-hop, and metrics"],
            ["t2t.session", "fsm.py, scoring.py, db.py", "Session FSM, SQLite WAL repository, time-decay and AST anti-drift scoring"],
            ["t2t.ai", "mentor.py, redactor.py, prompts.py", "Socratic AI mentor with credential redaction and banned-syntax filtering"],
            ["t2t.web / cli", "web/app.py, cli/app.py", "GET-only FastAPI SVG telemetry server and Rich Typer CLI application"],
        ],
        "Table 6.1 Module Architecture Specifications",
        [1.15, 1.9, 2.95],
    )

    add_section_heading("6.3 Security Features")
    add_table_data(
        ["Security Control", "Threat Mitigated", "Implementation Mechanism"],
        [
            ["Credential Isolation", "Secret leakage in code/Git", "Credentials resolved exclusively via env vars (T2T_SSH_USER/PASS)"],
            ["Regex Redaction Guard", "LLM leaking secrets or answers", "Pre/post-prompt regex strips passwords, IPs, and direct CLI commands"],
            ["Read-Only Audit Mode", "Accidental production mutation", "DeviceSession.push_config raises RuntimeError when read_only=True"],
            ["Localhost Bind Policy", "Unauthorized remote web access", "Binds 127.0.0.1; refuses 0.0.0.0 unless --allow-remote AND bearer token"],
            ["Parameterized SQL", "SQL injection via config inputs", "Strict parameter binding across all SQLite WAL queries"],
        ],
        "Table 6.2 Security Controls & Compliance Matrix",
        [1.45, 1.7, 2.85],
    )

    add_section_heading("6.4 Coding Standards")
    add_bullet_p("Full PEP 484 type hints verified with strict Mypy across all 52 source modules (0 errors).", bold_prefix="Strict Static Typing: ")
    add_bullet_p("Ruff enforces PEP 8 style, import sorting, and dead-code checks across the repository.", bold_prefix="Automated Linting: ")
    add_bullet_p("Per AGENTS.md Rule 10, zero time.sleep calls exist; injectable Clock enables instant deterministic tests.", bold_prefix="Injectable Clock: ")
    add_bullet_p("Conventional Commits (feat, fix, test) and strict Phase Gate traceability maintain auditability.", bold_prefix="Version Discipline: ")

    # ------------------------------------------------------------------
    # CHAPTER 7: TESTING
    # ------------------------------------------------------------------
    s_ch7 = doc.add_section()
    set_section_margins(s_ch7)
    style_header_footer(s_ch7, "Chapter 7: Testing", is_roman=False)

    add_chapter_heading("CHAPTER 7: TESTING")

    add_section_heading("7.1 Testing Plan")
    add_body_p(
        "Verification followed a five-tier test plan spanning Unit Testing, Static Audit Validation, Offline Mock "
        "Replay Parity, FastAPI Contract Testing, and Live Lab Qualification. Every phase gate required 100% pass "
        "status alongside clean Ruff and Mypy runs before advancing."
    )

    add_section_heading("7.2 Testing Strategy")
    add_table_data(
        ["Testing Tier", "Target Scope", "Framework / Tooling", "Exit Criteria"],
        [
            ["Unit Testing", "AST grammar, regex tokens, scoring math, FSM", "Pytest, MockClock", "100% pass; 0 warnings"],
            ["Static Audit Tests", "Rules A1–A7 on clean & faulty IOS-XE configs", "Pytest, Config Fixtures", "All anomalies flagged"],
            ["Replay Parity", "DeviceSession playback on captured CLI logs", "Pytest, MockDevice", "Matches live router output"],
            ["Contract Tests", "FastAPI GET-only routes, 0.0.0.0 bind refusal", "FastAPI TestClient", "Non-GET & unsafe bind blocked"],
            ["Lab Qualification", "End-to-end fault injection on CSR1000v lab", "t2t qualify CLI, SSH", "3/3 consecutive passes"],
        ],
        "Table 7.1 Testing Strategy and Methodology Matrix",
        [1.25, 2.1, 1.35, 1.3],
    )

    add_section_heading("7.3 Test Suites Design & Verification Execution")
    add_body_p(
        "All 129 automated tests across Phase Gates U1.1–U10.3 execute in 10.13 seconds with a 100% pass rate "
        "(0 failures, 0 mypy errors, 0 ruff issues). Table 7.2 summarizes the verified phase-gate test matrix."
    )

    add_table_data(
        ["Gate ID", "Module / Phase", "Representative Test Scenarios Verified", "Expected Outcome", "Status"],
        [
            ["U1.1–U1.2", "Ph 1: Baseline", "Load YAML inventory; validate 4-router subnets & links", "Valid topology schema & IP plan", "PASS"],
            ["U2.1–U2.3", "Ph 2: Parsers", "Parse hierarchical EIGRP, OSPF, route-map, prefix-list blocks", "Accurate structured AST trees", "PASS"],
            ["U3.1–U3.3", "Ph 3: Audit", "Evaluate Rules A1 (seed), A3 (tags), A5 (AD inversion)", "Critical/High violations flagged", "PASS"],
            ["U4.1–U4.2", "Ph 4: Devices", "Replay fixture lookup; block push_config on read_only device", "Exact replay; RuntimeError raised", "PASS"],
            ["U5.1–U5.2", "Ph 5: Faults", "Validate YAML fault catalog (T1–T7) & inject T3 on ASBRs", "Clean schema & targeted injection", "PASS"],
            ["U6.1–U6.2", "Ph 6: Verify", "Oracle checks baseline convergence vs inverted T3 protocol", "Baseline PASS; c_t3_r3 FAIL", "PASS"],
            ["U7.1–U7.2", "Ph 7: Scoring", "Score zero-drift fast fix vs high-drift noisy submission", "98.5/100 vs penalized drift score", "PASS"],
            ["U8.1–U8.2", "Ph 8: AI Mentor", "Generate Socratic hint; redact passwords, IPs & CLI answers", "Guiding question; [REDACTED] tags", "PASS"],
            ["U9.1", "Ph 9: Packaging", "Run 't2t demo' outside git repo using packaged fixtures", "Fallback inventory & replay PASS", "PASS"],
            ["U9.2", "Ph 9: Docker", "Build container image & execute 'docker run t2t demo'", "Zero-error containerized walkthrough", "PASS"],
            ["U10.1", "Ph 10: Web API", "GET /api/status, /api/session, /api/history, /api/audit/latest", "Valid JSON contracts (200 OK)", "PASS"],
            ["U10.2–U10.3", "Ph 10: Security", "Assert zero non-GET routes; refuse 0.0.0.0 without flag+token", "Mutation absent; unsafe bind denied", "PASS"],
        ],
        "Table 7.2 Comprehensive Test Suites & Verification Execution Results (U1.1 to U10.3)",
        [0.85, 1.1, 2.05, 1.45, 0.55],
    )

    # ------------------------------------------------------------------
    # CHAPTER 8: CONCLUSION AND DISCUSSION
    # ------------------------------------------------------------------
    s_ch8 = doc.add_section()
    set_section_margins(s_ch8)
    style_header_footer(s_ch8, "Chapter 8: Conclusion and Discussion", is_roman=False)

    add_chapter_heading("CHAPTER 8: CONCLUSION AND DISCUSSION")

    add_section_heading("8.1 Self-Analysis of Project Viabilities")
    add_body_p(
        "Post-implementation evaluation confirms strong viability across technical, economic, operational, schedule, "
        "and ethical dimensions (Table 8.1)."
    )

    add_table_data(
        ["Viability Dimension", "Evaluation Criteria", "Assessment & Supporting Evidence"],
        [
            ["Technical Viability", "Determinism, parsing accuracy, reliability", "129/129 passing tests; AST & oracle remove grading ambiguity."],
            ["Economic Viability", "Capital and licensing expenses", "100% open-source stack; offline replay removes physical rack cost."],
            ["Operational Viability", "Ease of onboarding & classroom utility", "Rich CLI + zero-config read-only SVG web dashboard."],
            ["Schedule Viability", "Delivery within 14-week semester", "All 10 phase gates completed on time via TDD milestones."],
            ["Legal & Ethical", "Licensing, safety, anti-plagiarism", "MIT/Apache deps; secret redaction; plagiarism <35% (<2%/source)."],
        ],
        "Table 8.1 Self-Analysis of Project Viabilities",
        [1.35, 1.65, 3.0],
    )

    add_section_heading("8.2 Problems Encountered and Possible Solutions")
    add_table_data(
        ["Obstacle Encountered", "Technical Root Cause", "Engineering Solution Implemented"],
        [
            ["Suboptimal Routing (Ticket T3)", "OSPF external AD (110) beat EIGRP external AD (170) on ASBRs, causing feedback.", "Applied 'distance ospf external 171' and route-map tag filtering (Tag 110/120)."],
            ["SSH Latency in CI Tests", "Live SSH sessions took 3–5s per command, slowing regression tests.", "Built MockDevice replay harness serving real captured IOS-XE outputs in <0.01s."],
            ["IOS-XE Config Reordering", "Routers reorder non-sequential lines on write memory, breaking text diffs.", "Replaced string comparison with logical, normalized RedistributionAST trees."],
            ["Student Config Churn", "Trial-and-error pasting could accidentally pass basic reachability checks.", "Engineered AST Levenshtein anti-drift penalties to reward minimal canonical fixes."],
            ["LLM Direct Answer Leaks", "Unconstrained models output exact CLI fixes, defeating learning goals.", "Enforced Socratic system prompts plus post-generation regex syntax redaction."],
            ["Packaged Demo Path Error", "Containerized 't2t demo' failed when lab/inventory.yaml was absent.", "Bundled demo_data fallback fixtures inside wheel and verified via U9.1–U9.2."],
        ],
        "Table 8.2 Technical Obstacles Encountered and Engineering Solutions",
        [1.55, 2.05, 2.4],
    )

    add_section_heading("8.3 Summary of Project Work")
    add_body_p(
        "Ticket-to-Topology delivered a complete, production-quality routing redistribution simulator and static "
        "configuration auditing suite across 52 typed Python modules and 129 passing tests. It unifies hierarchical "
        "Cisco IOS-XE AST parsing, seven static audit rules (A1–A7), seven fault scenarios (T1–T7), a zero-AI "
        "Verification Oracle, SQLite WAL state persistence, a regex-guarded Socratic AI mentor, and a read-only "
        "FastAPI SVG telemetry dashboard."
    )
    add_body_p(
        "By decoupling deterministic control-plane verification from probabilistic AI tutoring, the platform proves "
        "that advanced CCNP Enterprise redistribution diagnostics—including metric translation, route tagging, and AD "
        "inversion remediation—can be taught interactively and audited reliably with complete academic integrity."
    )

    # ------------------------------------------------------------------
    # CHAPTER 9: LIMITATION AND FUTURE ENHANCEMENT
    # ------------------------------------------------------------------
    s_ch9 = doc.add_section()
    set_section_margins(s_ch9)
    style_header_footer(s_ch9, "Chapter 9: Limitation and Future Enhancement", is_roman=False)

    add_chapter_heading("CHAPTER 9: LIMITATION AND FUTURE ENHANCEMENT")

    add_section_heading("9.1 Project Limitations")
    add_bullet_p("The reference lab models a fixed 4-router dual-ASBR core (R1–R4); arbitrary N-ASBR topologies are not yet parameterized.", bold_prefix="Topology Specialization: ")
    add_bullet_p("The AST tokenizer targets Cisco IOS-XE CLI syntax exclusively and does not yet parse Arista EOS or Juniper Junos.", bold_prefix="Single-Vendor Syntax: ")
    add_bullet_p("Socratic AI hints require local Ollama compute or external API keys; air-gapped hosts fall back to static hint catalogs.", bold_prefix="AI Compute Dependency: ")
    add_bullet_p("Current routing invariants and audit rules cover IPv4 unicast only, excluding OSPFv3 and EIGRP for IPv6.", bold_prefix="IPv4 Unicast Scope: ")

    add_section_heading("9.2 Future Enhancements")
    add_bullet_p("Extend the AST parser and audit rules to support MP-BGP EVPN/VXLAN and IPv6 mutual redistribution scenarios.", bold_prefix="BGP EVPN & IPv6 Support: ")
    add_bullet_p("Add OpenConfig/YANG adapters to enable cross-vendor redistribution troubleshooting across Cisco, Arista, and Juniper.", bold_prefix="Multi-Vendor OpenConfig: ")
    add_bullet_p("Embed an opt-in xterm.js console panel for sandboxed labs while keeping the audit server strictly read-only.", bold_prefix="Interactive Web Console: ")
    add_bullet_p("Integrate Containerlab and Cisco CML APIs to provision custom virtual router topologies dynamically per ticket.", bold_prefix="Dynamic Lab Provisioning: ")

    # ------------------------------------------------------------------
    # REFERENCES
    # ------------------------------------------------------------------
    s_ref = doc.add_section()
    set_section_margins(s_ref)
    style_header_footer(s_ref, "References", is_roman=False)

    add_chapter_heading("REFERENCES")

    references = [
        '[1] J. Moy, "OSPF Version 2," Internet Engineering Task Force (IETF), RFC 2328, Standard 54, Apr. 1998.',
        '[2] D. Savage, J. Ng, S. Moore, D. Slice, P. Paluch, and R. White, "Cisco\'s Enhanced Interior Gateway Routing Protocol (EIGRP)," RFC 7868, May 2016.',
        '[3] B. Edelman, R. Anthony, and D. Hucaby, CCNP and CCIE Enterprise Core ENCOR 350-401 Official Cert Guide, 2nd ed. Indianapolis, IN: Cisco Press, 2023.',
        '[4] R. Lacoste and B. Edelman, CCNP Enterprise Advanced Routing ENARSI 300-410 Official Cert Guide, 2nd ed. Indianapolis, IN: Cisco Press, 2023.',
        '[5] A. Fogel et al., "A General Approach to Network Configuration Analysis," in Proc. USENIX NSDI, Oakland, CA, 2015, pp. 469–483.',
        '[6] K. Byers, "Netmiko: Multi-vendor library to simplify Paramiko SSH connections to network devices." [Online]. Available: https://github.com/ktbyers/netmiko',
        '[7] Cisco Systems Inc., "Cisco pyATS & Genie Parser Framework Documentation." [Online]. Available: https://pubhub.devnetcloud.com/media/pyats/docs/',
        '[8] S. Ramirez, "FastAPI: Modern, Fast Web Framework for Building APIs with Python." [Online]. Available: https://fastapi.tiangolo.com/',
        '[9] D. Hipp, "SQLite Write-Ahead Logging (WAL) Architecture." [Online]. Available: https://www.sqlite.org/wal.html',
        '[10] A. Tack and C. Piech, "The Socratic Method in Conversational AI for Education," in Proc. Int. Conf. AI in Education (AIED), 2022, pp. 312–324.',
        '[11] R. S. Pressman and B. R. Maxim, Software Engineering: A Practitioner\'s Approach, 9th ed. New York, NY: McGraw-Hill Education, 2020.',
        '[12] I. Sommerville, Software Engineering, 10th ed. Boston, MA: Pearson Education, 2016.',
        '[13] Python Software Foundation, "PEP 484 – Type Hints and Mypy Static Typing." [Online]. Available: https://peps.python.org/pep-0484/',
        '[14] Astral Software, "Ruff: An Extremely Fast Python Linter and Formatter." [Online]. Available: https://docs.astral.sh/ruff/',
        '[15] Cisco Systems Inc., "Redistributing Routing Protocols: Cisco IOS-XE Configuration Guide," San Jose, CA, 2024.',
        '[16] W. Stallings, Data and Computer Communications, 10th ed. Upper Saddle River, NJ: Pearson Prentice Hall, 2014.',
    ]
    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.line_spacing = 1.12
        p_ref.paragraph_format.space_after = Pt(3)
        p_ref.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p_ref.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10.5)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_PATH))
    return OUT_PATH


def query_exact_pages_with_word(docx_path: Path, targets: list[str]) -> tuple[dict[str, str], int] | None:
    """
    Uses Microsoft Word COM via PowerShell (Windows only) to read exact rendered page numbers
    for every TOC heading, Figure caption, and Table caption, plus total Arabic chapter page count.
    Returns None gracefully if Word is unavailable.
    """
    if sys.platform != "win32":
        return None

    import os
    env = os.environ.copy()
    env["T2T_DOC_PATH"] = str(docx_path)
    env["T2T_TARGETS_JSON"] = json.dumps(targets)

    ps_script = r"""
$DocPath = $env:T2T_DOC_PATH
$targets = ConvertFrom-Json $env:T2T_TARGETS_JSON
$word = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($DocPath, $false, $true)
    $doc.Repaginate()
    $result = @{}
    $seen = @{}
    foreach ($p in $doc.Paragraphs) {
        $txt = $p.Range.Text.Trim()
        if ($txt -and ($targets -contains $txt) -and (-not $seen.ContainsKey($txt))) {
            # wdActiveEndAdjustedPageNumber = 1
            $pg = [int]$p.Range.Information(1)
            $result[$txt] = $pg
            $seen[$txt] = $true
        }
    }
    $lastPg = [int]$doc.Paragraphs.Last.Range.Information(1)
    $doc.Close($false)
    $word.Quit()
    [PSCustomObject]@{ pages = $result; last_arabic = $lastPg } | ConvertTo-Json -Depth 4
} catch {
    if ($word) { try { $word.Quit() } catch {} }
    exit 1
}
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            env=env,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        payload = json.loads(proc.stdout)
        raw_pages = payload.get("pages", {})
        last_arabic = int(payload.get("last_arabic", 0))
        roman_keys = {"ABSTRACT", "ACKNOWLEDGEMENT", "TABLE OF CONTENT", "LIST OF FIGURES", "LIST OF TABLES"}
        mapped: dict[str, str] = {}
        for k, v in raw_pages.items():
            mapped[k] = to_roman(int(v)) if k in roman_keys else str(int(v))
        return mapped, last_arabic
    except Exception:
        return None


if __name__ == "__main__":
    # Pass 1: Build with calibrated defaults
    path = create_report(DEFAULT_PAGE_MAP)
    print(f"Pass 1 generated: {path}")

    # Pass 2: If MS Word is available on Windows, sync exact rendered page numbers into TOC, LOF, LOT
    all_keys = list(DEFAULT_PAGE_MAP.keys())
    exact = query_exact_pages_with_word(path, all_keys)
    if exact:
        exact_map, last_page = exact
        merged = {**DEFAULT_PAGE_MAP, **exact_map}
        path = create_report(merged)
        # Re-verify after table rebuild in case TOC row counts shifted anything
        exact2 = query_exact_pages_with_word(path, all_keys)
        if exact2:
            exact_map2, last_page = exact2
            merged2 = {**merged, **exact_map2}
            path = create_report(merged2)
        print(f"Pass 2 (exact MS Word pagination synced): {path}")
        print(f"Verified rendered length (Chapter 1 through References): {last_page} pages")
    else:
        print("MS Word COM unavailable; report saved with calibrated ~30-page TOC/LOF/LOT numbering.")
