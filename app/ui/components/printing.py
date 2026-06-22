"""مساعد طباعة/تصدير كشوف الحساب عبر QTextDocument.

يبني مستندًا من HTML (يدعم العربية وRTL) ويطبعه عبر حوار الطباعة، أو يصدّره
PDF إلى ملف يختاره المستخدم. حوار الطباعة/اختيار الملف استثناءات مسموح بها.
"""
from __future__ import annotations

from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget


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
