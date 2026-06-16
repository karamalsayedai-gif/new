import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/app_theme.dart';
import '../models/customer.dart';
import '../models/transaction.dart';
import '../providers/transaction_provider.dart';
import '../utils/currencies.dart';
import '../utils/image_storage.dart';

class AddTransactionScreen extends StatefulWidget {
  final Customer customer;
  final TransactionType initialType;
  final Transaction? transaction;

  const AddTransactionScreen({
    super.key,
    required this.customer,
    required this.initialType,
    this.transaction,
  });

  @override
  State<AddTransactionScreen> createState() => _AddTransactionScreenState();
}

class _AddTransactionScreenState extends State<AddTransactionScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _amountController;
  late final TextEditingController _noteController;
  late final TextEditingController _rateController;
  late TransactionType _type;
  late DateTime _selectedDate;
  late String _currency;
  String? _imagePath;
  bool _isLoading = false;

  bool get _isEditing => widget.transaction != null;
  bool get _isForeignCurrency => !Currencies.isBase(_currency);

  @override
  void initState() {
    super.initState();
    _type = widget.initialType;
    _selectedDate = widget.transaction?.date ?? DateTime.now();
    _currency = widget.transaction?.currency ?? Currencies.base;
    _imagePath = widget.transaction?.imagePath;
    _amountController = TextEditingController(
      text: widget.transaction != null
          ? widget.transaction!.amount.toString()
          : '',
    );
    _noteController = TextEditingController(
      text: widget.transaction?.note ?? '',
    );
    _rateController = TextEditingController(
      text: widget.transaction?.exchangeRate?.toString() ??
          (_isForeignCurrency
              ? Currencies.byCode(_currency).defaultRate.toString()
              : ''),
    );
  }

  @override
  void dispose() {
    _amountController.dispose();
    _noteController.dispose();
    _rateController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDebit = _type == TransactionType.debit;
    final color = isDebit ? AppColors.debit : AppColors.credit;
    final bgColor = isDebit ? AppColors.debitLight : AppColors.creditLight;

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditing ? 'تعديل معاملة' : 'معاملة جديدة'),
        backgroundColor:
            isDebit ? AppColors.debit : AppColors.credit,
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Customer Info
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Center(
                      child: Text(
                        widget.customer.initials,
                        style: TextStyle(
                          color: color,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.customer.name,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      if (widget.customer.phone != null)
                        Text(
                          widget.customer.phone!,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: AppColors.textHint),
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Type Toggle
            Text(
              'نوع المعاملة',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _TypeButton(
                    label: 'أعطيت',
                    sublabel: 'أعطيته فلوس',
                    icon: Icons.arrow_upward_rounded,
                    isSelected: _type == TransactionType.debit,
                    color: AppColors.debit,
                    bgColor: AppColors.debitLight,
                    onTap: () =>
                        setState(() => _type = TransactionType.debit),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _TypeButton(
                    label: 'أخذت',
                    sublabel: 'أخذت منه فلوس',
                    icon: Icons.arrow_downward_rounded,
                    isSelected: _type == TransactionType.credit,
                    color: AppColors.credit,
                    bgColor: AppColors.creditLight,
                    onTap: () =>
                        setState(() => _type = TransactionType.credit),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Amount + Currency
            Row(
              children: [
                Text(
                  'المبلغ',
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const Spacer(),
                _buildCurrencyDropdown(),
              ],
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _amountController,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 28,
                fontWeight: FontWeight.w700,
                color: color,
              ),
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                hintText: '0.00',
                hintStyle: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textHint,
                ),
                suffixText: _currency,
                suffixStyle: TextStyle(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
                filled: true,
                fillColor: bgColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide(color: color, width: 2),
                ),
              ),
              validator: (v) {
                if (v == null || v.trim().isEmpty) {
                  return 'يرجى إدخال المبلغ';
                }
                final amount = double.tryParse(v);
                if (amount == null || amount <= 0) {
                  return 'يرجى إدخال مبلغ صحيح';
                }
                return null;
              },
            ),
            if (_isForeignCurrency) ...[
              const SizedBox(height: 12),
              _buildExchangeRateField(),
            ],
            const SizedBox(height: 20),

            // Quick amounts
            Wrap(
              spacing: 8,
              children: [50, 100, 200, 500, 1000, 2000].map((amt) {
                return ActionChip(
                  label: Text('$amt'),
                  onPressed: () =>
                      _amountController.text = amt.toString(),
                );
              }).toList(),
            ),
            const SizedBox(height: 20),

            // Date
            Text(
              'التاريخ',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            GestureDetector(
              onTap: _pickDate,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Theme.of(context).brightness == Brightness.dark
                      ? AppColors.darkCard
                      : Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.calendar_today_rounded,
                        color: AppColors.primary, size: 20),
                    const SizedBox(width: 12),
                    Text(
                      DateFormat('EEEE, dd MMMM yyyy', 'ar')
                          .format(_selectedDate),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // Note
            Text(
              'ملاحظة (اختياري)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _noteController,
              textDirection: TextDirection.rtl,
              maxLines: 3,
              decoration: const InputDecoration(
                hintText: 'أضف ملاحظة عن المعاملة...',
                prefixIcon: Icon(Icons.notes_rounded),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 20),

            // Receipt Image
            Text(
              'صورة الإيصال (اختياري)',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
            ),
            const SizedBox(height: 8),
            _buildImageSection(color, bgColor),
            const SizedBox(height: 32),

            // Save Button
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: color,
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Text(
                        _isEditing
                            ? 'حفظ التعديلات'
                            : 'تسجيل ${isDebit ? 'أعطيت' : 'أخذت'}',
                        style: const TextStyle(fontSize: 16),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCurrencyDropdown() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: _currency,
          isDense: true,
          icon: const Icon(Icons.keyboard_arrow_down_rounded,
              color: AppColors.primary, size: 18),
          style: const TextStyle(
            color: AppColors.primary,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
          items: Currencies.all.map((c) {
            return DropdownMenuItem(
              value: c.code,
              child: Text('${c.code} · ${c.name}'),
            );
          }).toList(),
          onChanged: (value) {
            if (value == null) return;
            setState(() {
              _currency = value;
              if (_isForeignCurrency) {
                _rateController.text =
                    Currencies.byCode(value).defaultRate.toString();
              }
            });
          },
        ),
      ),
    );
  }

  Widget _buildExchangeRateField() {
    final amount = double.tryParse(_amountController.text) ?? 0;
    final rate = double.tryParse(_rateController.text) ?? 0;
    final converted = amount * rate;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.accentLight.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.accent.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              const Icon(Icons.currency_exchange_rounded,
                  color: AppColors.accentDark, size: 18),
              const SizedBox(width: 8),
              Text(
                'سعر الصرف (1 $_currency =)',
                style: const TextStyle(
                    color: AppColors.accentDark,
                    fontSize: 12,
                    fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              SizedBox(
                width: 90,
                child: TextFormField(
                  controller: _rateController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  textAlign: TextAlign.center,
                  onChanged: (_) => setState(() {}),
                  style: const TextStyle(
                      fontWeight: FontWeight.w700, fontSize: 14),
                  decoration: InputDecoration(
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 8),
                    suffixText: Currencies.base,
                    suffixStyle: const TextStyle(fontSize: 11),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
            ],
          ),
          if (converted > 0) ...[
            const SizedBox(height: 8),
            Text(
              '= ${converted.toStringAsFixed(2)} ${Currencies.base}',
              style: const TextStyle(
                color: AppColors.accentDark,
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildImageSection(Color color, Color bgColor) {
    if (_imagePath != null && File(_imagePath!).existsSync()) {
      return Stack(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Image.file(
              File(_imagePath!),
              width: double.infinity,
              height: 180,
              fit: BoxFit.cover,
            ),
          ),
          Positioned(
            top: 8,
            left: 8,
            child: GestureDetector(
              onTap: () => setState(() => _imagePath = null),
              child: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.black54,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.close_rounded,
                    color: Colors.white, size: 18),
              ),
            ),
          ),
        ],
      );
    }

    return Row(
      children: [
        Expanded(
          child: _attachButton(
            icon: Icons.camera_alt_rounded,
            label: 'كاميرا',
            color: color,
            bgColor: bgColor,
            onTap: () => _pickImage(ImageSource.camera),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _attachButton(
            icon: Icons.photo_library_rounded,
            label: 'المعرض',
            color: color,
            bgColor: bgColor,
            onTap: () => _pickImage(ImageSource.gallery),
          ),
        ),
      ],
    );
  }

  Widget _attachButton({
    required IconData icon,
    required String label,
    required Color color,
    required Color bgColor,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.25)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                  color: color, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final path = await ImageStorage.pickAndSave(source);
      if (path != null && mounted) {
        setState(() => _imagePath = path);
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تعذّر إرفاق الصورة')),
        );
      }
    }
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2020),
      lastDate: DateTime.now(),
      locale: const Locale('ar'),
    );
    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    final amount = double.parse(_amountController.text);
    final rate = _isForeignCurrency
        ? (double.tryParse(_rateController.text) ??
            Currencies.byCode(_currency).defaultRate)
        : null;

    final transaction = Transaction(
      id: widget.transaction?.id,
      customerId: widget.customer.id!,
      type: _type,
      amount: amount,
      currency: _currency,
      exchangeRate: rate,
      note: _noteController.text.trim().isEmpty
          ? null
          : _noteController.text.trim(),
      imagePath: _imagePath,
      date: _selectedDate,
      createdAt: widget.transaction?.createdAt,
    );

    final provider = context.read<TransactionProvider>();

    if (_isEditing) {
      await provider.updateTransaction(transaction);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تم تعديل المعاملة')),
        );
      }
    } else {
      await provider.addTransaction(transaction);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              _type == TransactionType.debit
                  ? 'تم تسجيل أعطيت $amount ج.م'
                  : 'تم تسجيل أخذت $amount ج.م',
            ),
          ),
        );
      }
    }

    if (mounted) Navigator.pop(context);
  }
}

class _TypeButton extends StatelessWidget {
  final String label;
  final String sublabel;
  final IconData icon;
  final bool isSelected;
  final Color color;
  final Color bgColor;
  final VoidCallback onTap;

  const _TypeButton({
    required this.label,
    required this.sublabel,
    required this.icon,
    required this.isSelected,
    required this.color,
    required this.bgColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected ? color : bgColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected ? color : color.withOpacity(0.3),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(
              icon,
              color: isSelected ? Colors.white : color,
              size: 24,
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : color,
                fontWeight: FontWeight.w700,
                fontSize: 16,
              ),
            ),
            Text(
              sublabel,
              style: TextStyle(
                color: isSelected
                    ? Colors.white.withOpacity(0.8)
                    : color.withOpacity(0.7),
                fontSize: 11,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
