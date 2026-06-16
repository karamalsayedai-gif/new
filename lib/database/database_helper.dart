import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../models/customer.dart';
import '../models/transaction.dart';

class DatabaseHelper {
  static final DatabaseHelper _instance = DatabaseHelper._internal();
  static Database? _database;

  factory DatabaseHelper() => _instance;
  DatabaseHelper._internal();

  Future<Database> get database async {
    _database ??= await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'hesabati.db');
    return openDatabase(
      path,
      version: 2,
      onCreate: _onCreate,
      onUpgrade: _onUpgrade,
    );
  }

  Future<void> _onCreate(Database db, int version) async {
    await db.execute('''
      CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        notes TEXT,
        avatar_color TEXT,
        category INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        type INTEGER NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'ج.م',
        exchange_rate REAL,
        note TEXT,
        image_path TEXT,
        date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers (id) ON DELETE CASCADE
      )
    ''');
  }

  Future<void> _onUpgrade(Database db, int oldVersion, int newVersion) async {
    if (oldVersion < 2) {
      await db.execute(
          "ALTER TABLE customers ADD COLUMN category INTEGER NOT NULL DEFAULT 0");
      await db.execute(
          "ALTER TABLE transactions ADD COLUMN currency TEXT NOT NULL DEFAULT 'ج.م'");
      await db.execute(
          "ALTER TABLE transactions ADD COLUMN exchange_rate REAL");
      await db.execute(
          "ALTER TABLE transactions ADD COLUMN image_path TEXT");
    }
  }

  // ============ Customer Operations ============

  Future<int> insertCustomer(Customer customer) async {
    final db = await database;
    return db.insert('customers', customer.toMap());
  }

  Future<List<Customer>> getAllCustomers() async {
    final db = await database;
    final maps = await db.query('customers', orderBy: 'updated_at DESC');
    return maps.map((m) => Customer.fromMap(m)).toList();
  }

  Future<Customer?> getCustomer(int id) async {
    final db = await database;
    final maps = await db.query('customers', where: 'id = ?', whereArgs: [id]);
    if (maps.isEmpty) return null;
    return Customer.fromMap(maps.first);
  }

  Future<int> updateCustomer(Customer customer) async {
    final db = await database;
    return db.update(
      'customers',
      customer.copyWith(updatedAt: DateTime.now()).toMap(),
      where: 'id = ?',
      whereArgs: [customer.id],
    );
  }

  Future<int> deleteCustomer(int id) async {
    final db = await database;
    return db.delete('customers', where: 'id = ?', whereArgs: [id]);
  }

  Future<List<Customer>> searchCustomers(String query) async {
    final db = await database;
    final maps = await db.query(
      'customers',
      where: 'name LIKE ? OR phone LIKE ?',
      whereArgs: ['%$query%', '%$query%'],
      orderBy: 'name ASC',
    );
    return maps.map((m) => Customer.fromMap(m)).toList();
  }

  // ============ Transaction Operations ============

  Future<int> insertTransaction(Transaction transaction) async {
    final db = await database;
    final id = await db.insert('transactions', transaction.toMap());
    // Update customer's updatedAt
    await db.update(
      'customers',
      {'updated_at': DateTime.now().toIso8601String()},
      where: 'id = ?',
      whereArgs: [transaction.customerId],
    );
    return id;
  }

  Future<List<Transaction>> getCustomerTransactions(int customerId) async {
    final db = await database;
    final maps = await db.query(
      'transactions',
      where: 'customer_id = ?',
      whereArgs: [customerId],
      orderBy: 'date DESC',
    );
    return maps.map((m) => Transaction.fromMap(m)).toList();
  }

  Future<List<Transaction>> getAllTransactions() async {
    final db = await database;
    final maps = await db.query('transactions', orderBy: 'date DESC');
    return maps.map((m) => Transaction.fromMap(m)).toList();
  }

  Future<int> updateTransaction(Transaction transaction) async {
    final db = await database;
    return db.update(
      'transactions',
      transaction.toMap(),
      where: 'id = ?',
      whereArgs: [transaction.id],
    );
  }

  Future<int> deleteTransaction(int id) async {
    final db = await database;
    return db.delete('transactions', where: 'id = ?', whereArgs: [id]);
  }

  // ============ Balance Calculations ============

  // المبلغ بالعملة الأساسية = amount * exchange_rate (أو 1 لو مفيش سعر صرف)
  static const String _baseAmountExpr =
      'amount * COALESCE(exchange_rate, 1.0)';

  Future<double> getCustomerBalance(int customerId) async {
    final db = await database;
    final debitResult = await db.rawQuery(
      'SELECT SUM($_baseAmountExpr) as total FROM transactions WHERE customer_id = ? AND type = ?',
      [customerId, TransactionType.debit.index],
    );
    final creditResult = await db.rawQuery(
      'SELECT SUM($_baseAmountExpr) as total FROM transactions WHERE customer_id = ? AND type = ?',
      [customerId, TransactionType.credit.index],
    );
    final debit = (debitResult.first['total'] as num?)?.toDouble() ?? 0.0;
    final credit = (creditResult.first['total'] as num?)?.toDouble() ?? 0.0;
    return debit - credit; // positive = customer owes me, negative = I owe customer
  }

  Future<Map<String, double>> getTotals() async {
    final db = await database;
    final debitResult = await db.rawQuery(
      'SELECT SUM($_baseAmountExpr) as total FROM transactions WHERE type = ?',
      [TransactionType.debit.index],
    );
    final creditResult = await db.rawQuery(
      'SELECT SUM($_baseAmountExpr) as total FROM transactions WHERE type = ?',
      [TransactionType.credit.index],
    );
    final totalDebit = (debitResult.first['total'] as num?)?.toDouble() ?? 0.0;
    final totalCredit = (creditResult.first['total'] as num?)?.toDouble() ?? 0.0;
    return {
      'totalDebit': totalDebit,
      'totalCredit': totalCredit,
      'netBalance': totalDebit - totalCredit,
    };
  }

  Future<List<Map<String, dynamic>>> getMonthlyStats() async {
    final db = await database;
    return db.rawQuery('''
      SELECT
        strftime('%Y-%m', date) as month,
        SUM(CASE WHEN type = 1 THEN $_baseAmountExpr ELSE 0 END) as debit,
        SUM(CASE WHEN type = 0 THEN $_baseAmountExpr ELSE 0 END) as credit
      FROM transactions
      GROUP BY month
      ORDER BY month DESC
      LIMIT 6
    ''');
  }

  // ============ Backup / Restore / Clear ============

  Future<Map<String, dynamic>> exportData() async {
    final db = await database;
    final customers = await db.query('customers');
    final transactions = await db.query('transactions');
    return {
      'version': 2,
      'exported_at': DateTime.now().toIso8601String(),
      'customers': customers,
      'transactions': transactions,
    };
  }

  Future<void> importData(Map<String, dynamic> data) async {
    final db = await database;
    final batch = db.batch();
    batch.delete('transactions');
    batch.delete('customers');
    for (final c in (data['customers'] as List? ?? [])) {
      batch.insert('customers', Map<String, dynamic>.from(c));
    }
    for (final t in (data['transactions'] as List? ?? [])) {
      batch.insert('transactions', Map<String, dynamic>.from(t));
    }
    await batch.commit(noResult: true);
  }

  Future<void> clearAll() async {
    final db = await database;
    final batch = db.batch();
    batch.delete('transactions');
    batch.delete('customers');
    await batch.commit(noResult: true);
  }

  /// عملاء عليهم ديون قديمة بعد عدد أيام محدد (للتذكيرات)
  Future<List<Map<String, dynamic>>> getOverdueDebtors(int daysThreshold) async {
    final db = await database;
    final threshold = DateTime.now()
        .subtract(Duration(days: daysThreshold))
        .toIso8601String();
    return db.rawQuery('''
      SELECT c.id, c.name, c.phone,
        SUM(CASE WHEN t.type = 1 THEN $_baseAmountExpr ELSE -($_baseAmountExpr) END) as balance,
        MAX(t.date) as last_date
      FROM customers c
      JOIN transactions t ON t.customer_id = c.id
      GROUP BY c.id
      HAVING balance > 0 AND MAX(t.date) < ?
      ORDER BY balance DESC
    ''', [threshold]);
  }
}
