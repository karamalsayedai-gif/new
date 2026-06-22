"""مساعد طباعة/تصدير كشوف الحساب عبر QTextDocument.

يبني مستندًا من HTML (يدعم العربية وRTL) ويطبعه عبر حوار الطباعة، أو يصدّره
PDF إلى ملف يختاره المستخدم. حوار الطباعة/اختيار الملف استثناءات مسموح بها.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from app.core.constants.setting_keys import SettingKeys

if TYPE_CHECKING:
    from app.core.container import Container


def build_invoice_html(container: "Container", title: str, inner_html: str) -> str:
    """يلفّ محتوى الفاتورة بقالب طباعة قابل للتخصيص (ترويسة + تذييل من الإعدادات)."""
    s = container.settings
    name = s.showroom_name
    contact = ""
    if s.get_bool(SettingKeys.PRINT_SHOW_CONTACT):
        phone = s.get(SettingKeys.SHOWROOM_PHONE)
        addr = s.get(SettingKeys.SHOWROOM_ADDRESS)
        parts = [p for p in (phone, addr) if p]
        if parts:
            contact = f"<p style='text-align:center'>{' — '.join(parts)}</p>"
    header_note = s.get(SettingKeys.PRINT_HEADER)
    header_html = f"<p style='text-align:center'>{header_note}</p>" if header_note else ""
    footer = s.get(SettingKeys.PRINT_FOOTER)
    footer_html = (
        f"<hr><p style='text-align:center'>{footer}</p>" if footer else ""
    )
    return (
        f"<h2 style='text-align:center'>{name}</h2>{contact}{header_html}"
        f"<h3>{title}</h3>{inner_html}{footer_html}"
    )


def _build_document(html: str) -> QTextDocument:
    doc = QTextDocument()
    doc.setDefaultStyleSheet(
        "body { font-family: 'Segoe UI', Tahoma; } "
        "table { width: 100%; border-collapse: collapse; } "
        "th, td { border: 1px solid #999; padding: 6px; text-align: right; } "
        "th { background: #eee; } h2 { margin-bottom: 4px; }"
    )
    doc.setHtml(f"<div dir='rtl'>{html}</div>")
    return doc


def print_html(parent: QWidget, html: str, title: str = "طباعة") -> None:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(title)
    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return
    _build_document(html).print(printer)


def export_pdf(parent: QWidget, html: str, suggested_name: str = "statement.pdf") -> None:
    path, _ = QFileDialog.getSaveFileName(
        parent, "تصدير PDF", suggested_name, "PDF (*.pdf)"
    )
    if not path:
        return
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    _build_document(html).print(printer)
    QMessageBox.information(parent, "تم", f"تم تصدير الملف:\n{path}")
