import 'dart:typed_data';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import '../models/customer.dart';
import '../models/transaction.dart';
import 'formatters.dart';

class PdfGenerator {
  static const PdfColor _navy = PdfColor.fromInt(0xFF1E3A5F);
  static const PdfColor _navyLight = PdfColor.fromInt(0xFF2E5090);
  static const PdfColor _gold = PdfColor.fromInt(0xFFC8963E);
  static const PdfColor _debit = PdfColor.fromInt(0xFFE53935);
  static const PdfColor _credit = PdfColor.fromInt(0xFF26A69A);
  static const PdfColor _grey = PdfColor.fromInt(0xFF5A6478);
  static const PdfColor _lightBg = PdfColor.fromInt(0xFFF5F7FA);

  static Future<pw.Font> _arabicFont() =>
      PdfGoogleFonts.cairoRegular();
  static Future<pw.Font> _arabicBold() => PdfGoogleFonts.cairoBold();

  /// كشف حساب عميل واحد.
  static Future<Uint8List> customerStatement({
    required Customer customer,
    required List<Transaction> transactions,
    required double balance,
  }) async {
    final font = await _arabicFont();
    final bold = await _arabicBold();
    final doc = pw.Document();

    final theme = pw.ThemeData.withFont(base: font, bold: bold);

    doc.addPage(
      pw.MultiPage(
        theme: theme,
        textDirection: pw.TextDirection.rtl,
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(0),
        header: (context) => _header(customer),
        footer: (context) => _footer(context),
        build: (context) => [
          pw.Padding(
            padding: const pw.EdgeInsets.symmetric(horizontal: 28),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.stretch,
              children: [
                pw.SizedBox(height: 16),
                _balanceBanner(balance),
                pw.SizedBox(height: 20),
                _transactionsTable(transactions),
                pw.SizedBox(height: 16),
                _totalsRow(transactions, balance),
              ],
            ),
          ),
        ],
      ),
    );

    return doc.save();
  }

  static pw.Widget _header(Customer customer) {
    return pw.Container(
      width: double.infinity,
      padding: const pw.EdgeInsets.fromLTRB(28, 28, 28, 20),
      decoration: const pw.BoxDecoration(
        gradient: pw.LinearGradient(
          colors: [_navy, _navyLight],
          begin: pw.Alignment.topRight,
          end: pw.Alignment.bottomLeft,
        ),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Row(
            mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
            children: [
              pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Text('كشف حساب',
                      style: pw.TextStyle(
                          color: PdfColors.white,
                          fontSize: 24,
                          fontWeight: pw.FontWeight.bold)),
                  pw.SizedBox(height: 2),
                  pw.Text('تطبيق حساباتي',
                      style: pw.TextStyle(
                          color: _gold, fontSize: 12)),
                ],
              ),
              pw.Container(
                width: 54,
                height: 54,
                alignment: pw.Alignment.center,
                decoration: pw.BoxDecoration(
                  color: PdfColors.white,
                  borderRadius: pw.BorderRadius.circular(14),
                ),
                child: pw.Text('₪',
                    style: pw.TextStyle(
                        color: _navy,
                        fontSize: 26,
                        fontWeight: pw.FontWeight.bold)),
              ),
            ],
          ),
          pw.SizedBox(height: 18),
          pw.Container(
            padding: const pw.EdgeInsets.all(12),
            decoration: pw.BoxDecoration(
              color: PdfColors.white,
              borderRadius: pw.BorderRadius.circular(10),
            ),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text('العميل',
                        style: pw.TextStyle(color: _grey, fontSize: 9)),
                    pw.SizedBox(height: 2),
                    pw.Text(customer.name,
                        style: pw.TextStyle(
                            color: _navy,
                            fontSize: 15,
                            fontWeight: pw.FontWeight.bold)),
                    if (customer.phone != null &&
                        customer.phone!.isNotEmpty) ...[
                      pw.SizedBox(height: 2),
                      pw.Text(customer.phone!,
                          style: pw.TextStyle(color: _grey, fontSize: 10)),
                    ],
                  ],
                ),
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.end,
                  children: [
                    pw.Text('تاريخ الإصدار',
                        style: pw.TextStyle(color: _grey, fontSize: 9)),
                    pw.SizedBox(height: 2),
                    pw.Text(Formatters.date(DateTime.now()),
                        style: pw.TextStyle(
                            color: _navy,
                            fontSize: 13,
                            fontWeight: pw.FontWeight.bold)),
                    pw.SizedBox(height: 2),
                    pw.Text('${customer.category.label}',
                        style: pw.TextStyle(color: _gold, fontSize: 10)),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static pw.Widget _balanceBanner(double balance) {
    final isZero = balance.abs() < 0.01;
    final isPositive = balance > 0;
    final color = isZero ? _grey : (isPositive ? _debit : _credit);
    final label = isZero
        ? 'الحساب مسوّى'
        : (isPositive ? 'المستحق له عليّ' : 'المستحق عليه لي');

    return pw.Container(
      padding: const pw.EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: pw.BoxDecoration(
        color: PdfColor(color.red, color.green, color.blue, 0.08),
        borderRadius: pw.BorderRadius.circular(10),
        border: pw.Border.all(
            color: PdfColor(color.red, color.green, color.blue, 0.4)),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(label,
              style: pw.TextStyle(
                  color: color,
                  fontSize: 13,
                  fontWeight: pw.FontWeight.bold)),
          pw.Text(
              isZero ? '0' : Formatters.currency(balance.abs()),
              style: pw.TextStyle(
                  color: color,
                  fontSize: 20,
                  fontWeight: pw.FontWeight.bold)),
        ],
      ),
    );
  }

  static pw.Widget _transactionsTable(List<Transaction> transactions) {
    final headers = ['التاريخ', 'النوع', 'الملاحظة', 'المبلغ'];

    return pw.TableHelper.fromTextArray(
      headerAlignment: pw.Alignment.centerRight,
      cellAlignment: pw.Alignment.centerRight,
      headerDecoration: const pw.BoxDecoration(color: _navy),
      headerStyle: pw.TextStyle(
          color: PdfColors.white,
          fontSize: 11,
          fontWeight: pw.FontWeight.bold),
      cellStyle: const pw.TextStyle(fontSize: 10),
      rowDecoration: const pw.BoxDecoration(
        border: pw.Border(
            bottom: pw.BorderSide(color: _lightBg, width: 1)),
      ),
      oddRowDecoration: const pw.BoxDecoration(color: _lightBg),
      cellPadding:
          const pw.EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      columnWidths: {
        0: const pw.FlexColumnWidth(2),
        1: const pw.FlexColumnWidth(1.5),
        2: const pw.FlexColumnWidth(3),
        3: const pw.FlexColumnWidth(2),
      },
      headers: headers,
      data: transactions.map((t) {
        final amountStr =
            '${t.isDebit ? '+' : '-'} ${Formatters.currency(t.amount, symbol: t.currency)}';
        return [
          Formatters.date(t.date),
          t.typeLabel,
          (t.note == null || t.note!.isEmpty) ? '—' : t.note!,
          amountStr,
        ];
      }).toList(),
    );
  }

  static pw.Widget _totalsRow(
      List<Transaction> transactions, double balance) {
    final totalDebit = transactions
        .where((t) => t.isDebit)
        .fold<double>(0, (s, t) => s + t.baseAmount);
    final totalCredit = transactions
        .where((t) => t.isCredit)
        .fold<double>(0, (s, t) => s + t.baseAmount);

    return pw.Container(
      padding: const pw.EdgeInsets.all(14),
      decoration: pw.BoxDecoration(
        color: _lightBg,
        borderRadius: pw.BorderRadius.circular(10),
      ),
      child: pw.Column(
        children: [
          _totalLine('إجمالي أعطيت', totalDebit, _debit),
          pw.SizedBox(height: 6),
          _totalLine('إجمالي أخذت', totalCredit, _credit),
          pw.Divider(color: _grey),
          _totalLine(
            balance >= 0 ? 'الصافي (له عليّ)' : 'الصافي (عليه لي)',
            balance.abs(),
            balance >= 0 ? _debit : _credit,
            bold: true,
          ),
        ],
      ),
    );
  }

  static pw.Widget _totalLine(String label, double value, PdfColor color,
      {bool bold = false}) {
    return pw.Row(
      mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
      children: [
        pw.Text(label,
            style: pw.TextStyle(
                color: bold ? _navy : _grey,
                fontSize: bold ? 13 : 11,
                fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal)),
        pw.Text(Formatters.currency(value),
            style: pw.TextStyle(
                color: color,
                fontSize: bold ? 14 : 11,
                fontWeight: pw.FontWeight.bold)),
      ],
    );
  }

  static pw.Widget _footer(pw.Context context) {
    return pw.Container(
      padding: const pw.EdgeInsets.symmetric(horizontal: 28, vertical: 12),
      margin: const pw.EdgeInsets.only(top: 10),
      decoration: const pw.BoxDecoration(
        border: pw.Border(top: pw.BorderSide(color: _lightBg, width: 1)),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text('تم الإنشاء بواسطة تطبيق حساباتي',
              style: pw.TextStyle(color: _grey, fontSize: 9)),
          pw.Text('صفحة ${context.pageNumber} من ${context.pagesCount}',
              style: pw.TextStyle(color: _grey, fontSize: 9)),
        ],
      ),
    );
  }

  /// تقرير ملخّص بكل العملاء وأرصدتهم.
  static Future<Uint8List> summaryReport({
    required List<Customer> customers,
    required Map<int, double> balances,
    required double totalDebit,
    required double totalCredit,
  }) async {
    final font = await _arabicFont();
    final bold = await _arabicBold();
    final doc = pw.Document();
    final theme = pw.ThemeData.withFont(base: font, bold: bold);

    doc.addPage(
      pw.MultiPage(
        theme: theme,
        textDirection: pw.TextDirection.rtl,
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(0),
        header: (context) => pw.Container(
          width: double.infinity,
          padding: const pw.EdgeInsets.fromLTRB(28, 28, 28, 18),
          decoration: const pw.BoxDecoration(
            gradient: pw.LinearGradient(
              colors: [_navy, _navyLight],
              begin: pw.Alignment.topRight,
              end: pw.Alignment.bottomLeft,
            ),
          ),
          child: pw.Column(
            crossAxisAlignment: pw.CrossAxisAlignment.start,
            children: [
              pw.Text('تقرير شامل لكل العملاء',
                  style: pw.TextStyle(
                      color: PdfColors.white,
                      fontSize: 22,
                      fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 2),
              pw.Text(
                  'تطبيق حساباتي · ${Formatters.date(DateTime.now())}',
                  style: pw.TextStyle(color: _gold, fontSize: 11)),
            ],
          ),
        ),
        footer: _footer,
        build: (context) => [
          pw.Padding(
            padding: const pw.EdgeInsets.symmetric(horizontal: 28),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.stretch,
              children: [
                pw.SizedBox(height: 16),
                pw.Row(
                  children: [
                    pw.Expanded(
                        child: _summaryBox('عدد العملاء',
                            '${customers.length}', _navy)),
                    pw.SizedBox(width: 10),
                    pw.Expanded(
                        child: _summaryBox('إجمالي أعطيت',
                            Formatters.currency(totalDebit), _debit)),
                    pw.SizedBox(width: 10),
                    pw.Expanded(
                        child: _summaryBox('إجمالي أخذت',
                            Formatters.currency(totalCredit), _credit)),
                  ],
                ),
                pw.SizedBox(height: 18),
                pw.TableHelper.fromTextArray(
                  headerAlignment: pw.Alignment.centerRight,
                  cellAlignment: pw.Alignment.centerRight,
                  headerDecoration: const pw.BoxDecoration(color: _navy),
                  headerStyle: pw.TextStyle(
                      color: PdfColors.white,
                      fontSize: 11,
                      fontWeight: pw.FontWeight.bold),
                  cellStyle: const pw.TextStyle(fontSize: 10),
                  oddRowDecoration: const pw.BoxDecoration(color: _lightBg),
                  cellPadding: const pw.EdgeInsets.symmetric(
                      horizontal: 8, vertical: 8),
                  columnWidths: {
                    0: const pw.FlexColumnWidth(3),
                    1: const pw.FlexColumnWidth(2),
                    2: const pw.FlexColumnWidth(2),
                  },
                  headers: ['العميل', 'الحالة', 'الرصيد'],
                  data: customers.map((c) {
                    final bal = balances[c.id] ?? 0;
                    final status = bal.abs() < 0.01
                        ? 'مسوّى'
                        : (bal > 0 ? 'له عليّ' : 'عليه لي');
                    return [
                      '${c.category.emoji} ${c.name}',
                      status,
                      bal.abs() < 0.01
                          ? '—'
                          : Formatters.currency(bal.abs()),
                    ];
                  }).toList(),
                ),
              ],
            ),
          ),
        ],
      ),
    );

    return doc.save();
  }

  static pw.Widget _summaryBox(String label, String value, PdfColor color) {
    return pw.Container(
      padding: const pw.EdgeInsets.all(12),
      decoration: pw.BoxDecoration(
        color: PdfColor(color.red, color.green, color.blue, 0.08),
        borderRadius: pw.BorderRadius.circular(10),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(label, style: pw.TextStyle(color: _grey, fontSize: 9)),
          pw.SizedBox(height: 4),
          pw.Text(value,
              style: pw.TextStyle(
                  color: color,
                  fontSize: 13,
                  fontWeight: pw.FontWeight.bold)),
        ],
      ),
    );
  }

  /// يطبع أو يحفظ الـ PDF عبر واجهة النظام.
  static Future<void> printDocument(Uint8List bytes, String name) async {
    await Printing.layoutPdf(
      onLayout: (_) async => bytes,
      name: name,
    );
  }

  /// يشارك الـ PDF كملف.
  static Future<void> shareDocument(Uint8List bytes, String fileName) async {
    await Printing.sharePdf(bytes: bytes, filename: fileName);
  }
}
