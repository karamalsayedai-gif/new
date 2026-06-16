enum CustomerCategory {
  individual, // فرد
  merchant, // تاجر
  employee, // موظف
  company, // شركة
}

extension CustomerCategoryX on CustomerCategory {
  String get label {
    switch (this) {
      case CustomerCategory.individual:
        return 'فرد';
      case CustomerCategory.merchant:
        return 'تاجر';
      case CustomerCategory.employee:
        return 'موظف';
      case CustomerCategory.company:
        return 'شركة';
    }
  }

  String get emoji {
    switch (this) {
      case CustomerCategory.individual:
        return '🏠';
      case CustomerCategory.merchant:
        return '🏪';
      case CustomerCategory.employee:
        return '👷';
      case CustomerCategory.company:
        return '🏢';
    }
  }
}

class Customer {
  final int? id;
  final String name;
  final String? phone;
  final String? notes;
  final String? avatarColor;
  final CustomerCategory category;
  final DateTime createdAt;
  final DateTime updatedAt;

  Customer({
    this.id,
    required this.name,
    this.phone,
    this.notes,
    this.avatarColor,
    this.category = CustomerCategory.individual,
    DateTime? createdAt,
    DateTime? updatedAt,
  })  : createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();

  Customer copyWith({
    int? id,
    String? name,
    String? phone,
    String? notes,
    String? avatarColor,
    CustomerCategory? category,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Customer(
      id: id ?? this.id,
      name: name ?? this.name,
      phone: phone ?? this.phone,
      notes: notes ?? this.notes,
      avatarColor: avatarColor ?? this.avatarColor,
      category: category ?? this.category,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'name': name,
      'phone': phone,
      'notes': notes,
      'avatar_color': avatarColor,
      'category': category.index,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  factory Customer.fromMap(Map<String, dynamic> map) {
    return Customer(
      id: map['id'],
      name: map['name'],
      phone: map['phone'],
      notes: map['notes'],
      avatarColor: map['avatar_color'],
      category: map['category'] != null
          ? CustomerCategory.values[map['category']]
          : CustomerCategory.individual,
      createdAt: DateTime.parse(map['created_at']),
      updatedAt: DateTime.parse(map['updated_at']),
    );
  }

  String get initials {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    }
    return name.isNotEmpty ? name[0].toUpperCase() : '?';
  }

  /// رقم الهاتف بصيغة دولية لواتساب (يفترض مصر +20 لو الرقم محلي)
  String? get whatsappNumber {
    if (phone == null || phone!.trim().isEmpty) return null;
    var digits = phone!.replaceAll(RegExp(r'[^0-9]'), '');
    if (digits.isEmpty) return null;
    if (digits.startsWith('00')) {
      digits = digits.substring(2);
    } else if (digits.startsWith('0')) {
      digits = '20${digits.substring(1)}';
    }
    return digits;
  }
}
