enum TransactionType { credit, debit }

class Transaction {
  final int? id;
  final int customerId;
  final TransactionType type; // credit = أخذت مني, debit = أعطيت له
  final double amount;
  final String currency;
  final double? exchangeRate; // سعر الصرف مقابل العملة الأساسية
  final String? note;
  final String? imagePath; // مسار صورة الإيصال
  final DateTime date;
  final DateTime createdAt;

  Transaction({
    this.id,
    required this.customerId,
    required this.type,
    required this.amount,
    this.currency = 'ج.م',
    this.exchangeRate,
    this.note,
    this.imagePath,
    DateTime? date,
    DateTime? createdAt,
  })  : date = date ?? DateTime.now(),
        createdAt = createdAt ?? DateTime.now();

  bool get isCredit => type == TransactionType.credit;
  bool get isDebit => type == TransactionType.debit;

  bool get hasImage => imagePath != null && imagePath!.isNotEmpty;

  /// المبلغ محوّلاً للعملة الأساسية باستخدام سعر الصرف
  double get baseAmount => amount * (exchangeRate ?? 1.0);

  String get typeLabel => isDebit ? 'أعطيت' : 'أخذت';
  String get typeDescription => isDebit
      ? 'أعطيت له فلوس (دين عليه)'
      : 'أخذت منه فلوس (دين عليّ)';

  Transaction copyWith({
    int? id,
    int? customerId,
    TransactionType? type,
    double? amount,
    String? currency,
    double? exchangeRate,
    String? note,
    String? imagePath,
    DateTime? date,
    DateTime? createdAt,
  }) {
    return Transaction(
      id: id ?? this.id,
      customerId: customerId ?? this.customerId,
      type: type ?? this.type,
      amount: amount ?? this.amount,
      currency: currency ?? this.currency,
      exchangeRate: exchangeRate ?? this.exchangeRate,
      note: note ?? this.note,
      imagePath: imagePath ?? this.imagePath,
      date: date ?? this.date,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'customer_id': customerId,
      'type': type.index,
      'amount': amount,
      'currency': currency,
      'exchange_rate': exchangeRate,
      'note': note,
      'image_path': imagePath,
      'date': date.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
    };
  }

  factory Transaction.fromMap(Map<String, dynamic> map) {
    return Transaction(
      id: map['id'],
      customerId: map['customer_id'],
      type: TransactionType.values[map['type']],
      amount: (map['amount'] as num).toDouble(),
      currency: map['currency'] ?? 'ج.م',
      exchangeRate: (map['exchange_rate'] as num?)?.toDouble(),
      note: map['note'],
      imagePath: map['image_path'],
      date: DateTime.parse(map['date']),
      createdAt: DateTime.parse(map['created_at']),
    );
  }
}
