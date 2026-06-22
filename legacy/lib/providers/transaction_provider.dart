import 'package:flutter/material.dart';
import '../models/transaction.dart';
import '../database/database_helper.dart';

class TransactionProvider extends ChangeNotifier {
  final _db = DatabaseHelper();

  List<Transaction> _transactions = [];
  List<Map<String, dynamic>> _monthlyStats = [];
  bool _isLoading = false;

  List<Transaction> get transactions => _transactions;
  List<Map<String, dynamic>> get monthlyStats => _monthlyStats;
  bool get isLoading => _isLoading;

  Future<void> loadTransactions(int customerId) async {
    _isLoading = true;
    notifyListeners();
    _transactions = await _db.getCustomerTransactions(customerId);
    _isLoading = false;
    notifyListeners();
  }

  Future<void> loadMonthlyStats() async {
    _monthlyStats = await _db.getMonthlyStats();
    notifyListeners();
  }

  Future<Transaction> addTransaction(Transaction transaction) async {
    final id = await _db.insertTransaction(transaction);
    final newTx = transaction.copyWith(id: id);
    _transactions.insert(0, newTx);
    notifyListeners();
    return newTx;
  }

  Future<void> deleteTransaction(int id, int customerId) async {
    await _db.deleteTransaction(id);
    _transactions.removeWhere((t) => t.id == id);
    notifyListeners();
  }

  Future<void> updateTransaction(Transaction transaction) async {
    await _db.updateTransaction(transaction);
    final index = _transactions.indexWhere((t) => t.id == transaction.id);
    if (index != -1) {
      _transactions[index] = transaction;
    }
    notifyListeners();
  }

  double get totalDebit => _transactions
      .where((t) => t.isDebit)
      .fold(0, (sum, t) => sum + t.amount);

  double get totalCredit => _transactions
      .where((t) => t.isCredit)
      .fold(0, (sum, t) => sum + t.amount);

  double get balance => totalDebit - totalCredit;
}
