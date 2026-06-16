import 'package:flutter/material.dart';
import '../models/customer.dart';
import '../models/transaction.dart';
import '../database/database_helper.dart';

class CustomerProvider extends ChangeNotifier {
  final _db = DatabaseHelper();

  List<Customer> _customers = [];
  List<Customer> _filteredCustomers = [];
  Map<int, double> _balances = {};
  Map<String, double> _totals = {};
  bool _isLoading = false;
  String _searchQuery = '';
  CustomerCategory? _categoryFilter;

  List<Customer> get customers => _filteredCustomers;
  Map<int, double> get balances => _balances;
  Map<String, double> get totals => _totals;
  bool get isLoading => _isLoading;
  String get searchQuery => _searchQuery;
  CustomerCategory? get categoryFilter => _categoryFilter;

  double getBalance(int customerId) => _balances[customerId] ?? 0.0;

  Future<void> loadCustomers() async {
    _isLoading = true;
    notifyListeners();

    _customers = await _db.getAllCustomers();
    await _loadBalances();
    await _loadTotals();
    _applyFilter();

    _isLoading = false;
    notifyListeners();
  }

  Future<void> _loadBalances() async {
    for (final customer in _customers) {
      if (customer.id != null) {
        _balances[customer.id!] = await _db.getCustomerBalance(customer.id!);
      }
    }
  }

  Future<void> _loadTotals() async {
    _totals = await _db.getTotals();
  }

  void _applyFilter() {
    _filteredCustomers = _customers.where((c) {
      final matchesSearch = _searchQuery.isEmpty ||
          c.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          (c.phone?.contains(_searchQuery) ?? false);
      final matchesCategory =
          _categoryFilter == null || c.category == _categoryFilter;
      return matchesSearch && matchesCategory;
    }).toList();
  }

  void search(String query) {
    _searchQuery = query;
    _applyFilter();
    notifyListeners();
  }

  void setCategoryFilter(CustomerCategory? category) {
    _categoryFilter = category;
    _applyFilter();
    notifyListeners();
  }

  Future<Customer> addCustomer(Customer customer) async {
    final id = await _db.insertCustomer(customer);
    final newCustomer = customer.copyWith(id: id);
    _customers.insert(0, newCustomer);
    _balances[id] = 0.0;
    _applyFilter();
    notifyListeners();
    return newCustomer;
  }

  Future<void> updateCustomer(Customer customer) async {
    await _db.updateCustomer(customer);
    final index = _customers.indexWhere((c) => c.id == customer.id);
    if (index != -1) {
      _customers[index] = customer;
    }
    _applyFilter();
    notifyListeners();
  }

  Future<void> deleteCustomer(int id) async {
    await _db.deleteCustomer(id);
    _customers.removeWhere((c) => c.id == id);
    _balances.remove(id);
    await _loadTotals();
    _applyFilter();
    notifyListeners();
  }

  Future<void> refreshBalance(int customerId) async {
    _balances[customerId] = await _db.getCustomerBalance(customerId);
    await _loadTotals();
    notifyListeners();
  }

  Future<void> clearAll() async {
    await _db.clearAll();
    _customers.clear();
    _balances.clear();
    await _loadTotals();
    _applyFilter();
    notifyListeners();
  }

  List<Customer> get customersWithDebt =>
      _customers.where((c) => (_balances[c.id] ?? 0) > 0).toList();

  List<Customer> get customersIOwe =>
      _customers.where((c) => (_balances[c.id] ?? 0) < 0).toList();

  int get totalCustomers => _customers.length;
}
