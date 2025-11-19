# telegram_bot_api.py
# OPTIMIZED Telegram Bot API - To'liq va xatosiz versiya
# Barcha customer ma'lumotlari, mahsulotlar, to'lovlar
# ⚠️ MUHIM: Foiz yashirilgan - faqat yakuniy narx ko'rsatiladi

import frappe
from frappe.utils import flt, formatdate, getdate, nowdate, cstr
from frappe import _


# ============================================================
# 1) ASOSIY API - CUSTOMER SEARCH BY ID
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_by_id(customer_id, telegram_chat_id=None):
	"""
	Customer ID orqali to'liq ma'lumotlarni olish

	Qaytariladigan ma'lumotlar:
	- Customer asosiy ma'lumotlari (ism, familiya, telefon, passport)
	- Barcha shartnomalar batafsil:
	  * Mahsulotlar (nomi, soni, narxi = tan narx + foiz)
	  * To'lovlar tarixi (qachon, qancha)
	  * Qolgan qarz
	  * Keyingi to'lov sanasi

	Args:
		customer_id (str): Customer ID
		telegram_chat_id (str/int): Telegram chat ID (avtomatik bog'lash uchun)

	Returns:
		dict: To'liq customer ma'lumotlari
	"""
	if not customer_id:
		return {
			"success": False,
			"message": "Customer ID kiritilmagan",
			"message_uz": "ID kiritilmadi",
			"message_ru": "ID не введен"
		}

	try:
		# Customer mavjudligini tekshirish
		customer_exists = frappe.db.exists("Customer", customer_id)

		if not customer_exists:
			return {
				"success": False,
				"message": "Customer topilmadi",
				"message_uz": f"Mijoz topilmadi. ID ni tekshiring: {customer_id}",
				"message_ru": f"Клиент не найден. Проверьте ID: {customer_id}"
			}

		# Customer to'liq ma'lumotlarini olish
		customer_doc = frappe.get_doc("Customer", customer_id)

		# Customer asosiy ma'lumotlari
		customer = {
			"customer_id": customer_doc.name,
			"customer_name": customer_doc.customer_name or "",
			"phone": customer_doc.get("custom_phone_1") or "",
			"passport": customer_doc.get("custom_passport_series") or "",
			"classification": customer_doc.get("customer_classification") or "",
			"telegram_id": customer_doc.get("custom_telegram_id") or ""
		}

		# Telegram chat ID ni avtomatik bog'lash
		is_new_link = False
		if telegram_chat_id and not customer_doc.get("custom_telegram_id"):
			try:
				customer_doc.custom_telegram_id = str(telegram_chat_id)
				customer_doc.save(ignore_permissions=True)
				frappe.db.commit()

				customer["telegram_id"] = str(telegram_chat_id)
				is_new_link = True

				frappe.logger().info(
					f"✅ Telegram linked: Customer {customer_id} -> Chat ID {telegram_chat_id}"
				)
			except Exception as link_error:
				frappe.log_error(f"Error linking Telegram: {link_error}")

		# Shartnomalar va to'lovlar ma'lumotini olish (OPTIMIZED)
		contracts = get_customer_contracts_detailed(customer["customer_id"])
		next_payments = get_upcoming_payments(customer["customer_id"])

		return {
			"success": True,
			"customer": customer,
			"contracts": contracts.get("contracts", []),
			"next_payments": next_payments.get("payments", []),
			"is_new_link": is_new_link,
			"message": "Ma'lumotlar muvaffaqiyatli yuklandi"
		}

	except Exception as e:
		frappe.log_error(str(e), "Customer ID Search Error")
		return {
			"success": False,
			"message": f"Xatolik: {str(e)}",
			"message_uz": "Tizim xatosi. Iltimos qaytadan urinib ko'ring.",
			"message_ru": "Системная ошибка. Попробуйте снова."
		}


# ============================================================
# 2) OPTIMIZED CONTRACT DETAILS WITH PRODUCTS & PAYMENTS
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_contracts_detailed(customer_name):
	"""
	Customer ning barcha shartnomalarini BATAFSIL ma'lumot bilan olish

	OPTIMIZED VERSION - Batch queries ishlatilgan (N+1 muammosi hal qilingan)

	Har bir shartnoma uchun:
	- Asosiy ma'lumotlar (ID, sana, umumiy summa, to'langan, qolgan)
	- Mahsulotlar ro'yxati:
	  * Mahsulot nomi
	  * Soni
	  * Narxi (tan narx + foiz) - Installment Application dan
	  * IMEI / Serial number
	  * Izohlar
	- To'lovlar tarixi:
	  * To'lov sanasi
	  * To'langan summa
	  * To'lov usuli
	  * Payment ID
	- Keyingi to'lov ma'lumoti:
	  * To'lov sanasi
	  * To'lov miqdori
	  * Necha kun qolgan / kechikkan
	"""
	try:
		# 1. ASOSIY QUERY: Sales Orders + Installment Application info
		sales_orders = frappe.db.sql("""
			SELECT
				so.name,
				so.transaction_date,
				so.custom_grand_total_with_interest as total_with_interest,
				so.custom_downpayment_amount as downpayment,
				so.custom_total_interest as interest_amount,
				so.advance_paid,
				(so.custom_grand_total_with_interest - IFNULL(so.advance_paid, 0)) as remaining,
				so.status,
				ia.name as installment_app_id,
				ia.custom_total_interest as ia_total_interest,
				ia.total_amount as ia_total_amount
			FROM `tabSales Order` so
			LEFT JOIN `tabInstallment Application` ia
				ON ia.sales_order = so.name
			WHERE so.customer = %s
				AND so.docstatus = 1
				AND so.status != 'Cancelled'
			ORDER BY so.transaction_date DESC
		""", (customer_name,), as_dict=True)

		if not sales_orders:
			return {
				"success": True,
				"contracts": [],
				"message": "Shartnomalar topilmadi"
			}

		# IDs ni yig'ish batch queries uchun
		sales_order_ids = [so.name for so in sales_orders]
		installment_app_ids = [so.installment_app_id for so in sales_orders if so.installment_app_id]

		# 2. BATCH QUERY: Barcha mahsulotlarni bitta query bilan olish
		all_products = get_all_products_batch(installment_app_ids, sales_order_ids)

		# 3. BATCH QUERY: Barcha to'lovlarni bitta query bilan olish
		all_payments = get_all_payments_batch(sales_order_ids)

		# 4. BATCH QUERY: Keyingi to'lovlarni bitta query bilan olish
		all_next_payments = get_next_payment_batch(sales_order_ids)

		# 5. Ma'lumotlarni birlashtirish (hech qanday qo'shimcha query yo'q!)
		contracts_list = []

		for so in sales_orders:
			# Mahsulotlar - tan narx + foiz bilan hisoblangan
			products = calculate_products_with_interest(
				so.installment_app_id,
				so.name,
				all_products,
				flt(so.ia_total_interest) if so.ia_total_interest else 0,
				flt(so.ia_total_amount) if so.ia_total_amount else 0
			)

			# To'lovlar tarixi
			payments = all_payments.get(so.name, [])

			# Keyingi to'lov
			next_payment = all_next_payments.get(so.name)

			contracts_list.append({
				"contract_id": so.name,
				"contract_date": formatdate(so.transaction_date, "dd.MM.yyyy"),
				"total_amount": flt(so.total_with_interest),
				"downpayment": flt(so.downpayment),
				"paid": flt(so.advance_paid),
				"remaining": flt(so.remaining),
				"status": so.status,
				"status_uz": translate_status(so.status),
				"products": products,
				"payments_history": payments,
				"next_payment": next_payment,
				"total_payments": len(payments)
			})

		return {
			"success": True,
			"contracts": contracts_list,
			"total_contracts": len(contracts_list)
		}

	except Exception as e:
		frappe.log_error(str(e), "Get Contracts Detailed Error")
		return {
			"success": False,
			"message": str(e)
		}


# ============================================================
# 3) BATCH QUERY: BARCHA MAHSULOTLARNI OLISH
# ============================================================

def get_all_products_batch(installment_app_ids, sales_order_ids):
	"""
	Barcha shartnomalar uchun mahsulotlarni bitta query bilan olish

	Returns:
		dict: {
			"IA-00001": [products from Installment Application],
			"SAL-ORD-00001": [products from Sales Order - fallback]
		}
	"""
	all_products = {}

	try:
		# Installment Application dan mahsulotlar
		if installment_app_ids:
			ia_products = frappe.db.sql("""
				SELECT
					parent,
					item_name,
					qty,
					rate as base_price,
					amount as base_amount,
					custom_imei as imei,
					custom_notes as notes,
					idx
				FROM `tabInstallment Application Item`
				WHERE parent IN %(parents)s
				ORDER BY parent, idx
			""", {"parents": installment_app_ids}, as_dict=True)

			# Group by parent (Installment Application ID)
			for p in ia_products:
				if p.parent not in all_products:
					all_products[p.parent] = []
				all_products[p.parent].append(p)

		# Sales Order dan mahsulotlar (fallback - eski shartnomalar uchun)
		if sales_order_ids:
			so_products = frappe.db.sql("""
				SELECT
					parent,
					item_name,
					qty,
					rate,
					amount,
					custom_imei as imei,
					idx
				FROM `tabSales Order Item`
				WHERE parent IN %(parents)s
					AND item_name NOT LIKE '%%Foiz%%'
					AND item_name NOT LIKE '%%Interest%%'
				ORDER BY parent, idx
			""", {"parents": sales_order_ids}, as_dict=True)

			# Group by parent (Sales Order ID)
			for p in so_products:
				# Faqat Installment Application bo'lmagan shartnomalar uchun
				parent_key = f"SO_{p.parent}"
				if parent_key not in all_products:
					all_products[parent_key] = []
				all_products[parent_key].append(p)

	except Exception as e:
		frappe.log_error(f"Error getting products batch: {e}")

	return all_products


# ============================================================
# 4) MAHSULOTLAR NARXINI HISOBLASH (TAN NARX + FOIZ)
# ============================================================

def calculate_products_with_interest(installment_app_id, sales_order_id, all_products, total_interest, total_base):
	"""
	Mahsulotlar narxini to'g'ri hisoblash: Tan narx + Foiz

	⚠️ MUHIM: Customer faqat yakuniy narxni ko'radi!
	- Tan narx yashirilgan
	- Foiz yashirilgan
	- Faqat yakuniy narx (tan narx + foiz) ko'rsatiladi

	Args:
		installment_app_id: Installment Application ID
		sales_order_id: Sales Order ID
		all_products: Batch query natijasi
		total_interest: Umumiy foiz
		total_base: Umumiy tan narx

	Returns:
		list: [{"name": "iPhone 14", "qty": 1, "price": 1200.00, "imei": "...", "notes": "..."}]
	"""
	products = []

	try:
		# Installment Application dan mahsulotlar (preferred)
		if installment_app_id and installment_app_id in all_products:
			for product in all_products[installment_app_id]:
				# Har bir mahsulotga foizni proporsional taqsimlash
				product_ratio = flt(product.base_amount) / total_base if total_base > 0 else 0
				product_interest = total_interest * product_ratio

				# ✅ YAKUNIY NARX = Tan narx + Foiz
				# Bu customer ko'radigan narx
				final_price_per_item = (flt(product.base_amount) + product_interest) / flt(product.qty) if flt(product.qty) > 0 else 0

				products.append({
					"name": product.item_name,
					"qty": flt(product.qty),
					"price": round(final_price_per_item, 2),  # ✅ YAKUNIY NARX
					"total_price": round(flt(product.base_amount) + product_interest, 2),
					"imei": product.imei or "",
					"notes": product.notes or ""
				})

		# Sales Order dan mahsulotlar (fallback - eski shartnomalar)
		else:
			parent_key = f"SO_{sales_order_id}"
			if parent_key in all_products:
				for product in all_products[parent_key]:
					products.append({
						"name": product.item_name,
						"qty": flt(product.qty),
						"price": flt(product.rate),
						"total_price": flt(product.amount),
						"imei": product.imei or "",
						"notes": ""
					})

	except Exception as e:
		frappe.log_error(f"Error calculating products with interest: {e}")

	return products


# ============================================================
# 5) BATCH QUERY: BARCHA TO'LOVLARNI OLISH
# ============================================================

def get_all_payments_batch(sales_order_ids):
	"""
	Barcha shartnomalar uchun to'lovlar tarixini bitta query bilan olish

	Returns:
		dict: {
			"SAL-ORD-00001": [
				{"date": "15.10.2025", "amount": 250.00, "payment_id": "CIN-123", "method": "Naqd"},
				...
			]
		}
	"""
	all_payments = {}

	try:
		if not sales_order_ids:
			return all_payments

		# Bitta optimallashtirilgan query
		payments_data = frappe.db.sql("""
			SELECT
				pe.custom_contract_reference as contract,
				pe.name as payment_id,
				pe.posting_date,
				pe.paid_amount,
				pe.mode_of_payment
			FROM `tabPayment Entry` pe
			WHERE pe.custom_contract_reference IN %(contracts)s
				AND pe.docstatus = 1
				AND pe.payment_type = 'Receive'
			ORDER BY pe.custom_contract_reference, pe.posting_date DESC
		""", {"contracts": sales_order_ids}, as_dict=True)

		# Group by contract
		for p in payments_data:
			if p.contract not in all_payments:
				all_payments[p.contract] = []

			all_payments[p.contract].append({
				"date": formatdate(p.posting_date, "dd.MM.yyyy"),
				"amount": flt(p.paid_amount),
				"payment_id": p.payment_id,
				"method": p.mode_of_payment or "Naqd"
			})

	except Exception as e:
		frappe.log_error(f"Error getting payments batch: {e}")

	return all_payments


# ============================================================
# 6) BATCH QUERY: KEYINGI TO'LOVLARNI OLISH
# ============================================================

def get_next_payment_batch(sales_order_ids):
	"""
	Barcha shartnomalar uchun keyingi to'lovlarni bitta query bilan olish

	Returns:
		dict: {
			"SAL-ORD-00001": {
				"due_date": "15.11.2025",
				"amount": 250.00,
				"days_left": 5,
				"status": "soon"
			}
		}
	"""
	next_payments = {}

	try:
		if not sales_order_ids:
			return next_payments

		# Har bir shartnoma uchun birinchi to'lanmagan to'lovni topish
		schedules = frappe.db.sql("""
			SELECT
				ps.parent,
				ps.due_date,
				ps.payment_amount,
				ps.outstanding,
				ps.paid_amount,
				ps.idx,
				DATEDIFF(ps.due_date, CURDATE()) as days_left
			FROM `tabPayment Schedule` ps
			WHERE ps.parent IN %(parents)s
				AND ps.outstanding > 0
			ORDER BY ps.parent, ps.due_date ASC
		""", {"parents": sales_order_ids}, as_dict=True)

		# Har bir shartnoma uchun birinchi to'lovni olish
		for s in schedules:
			if s.parent not in next_payments:
				days_left = s.days_left or 0

				# Status aniqlash
				if days_left < 0:
					status = "overdue"
					status_text = f"{abs(days_left)} kun kechikkan"
					status_uz = "Kechikkan"
				elif days_left == 0:
					status = "today"
					status_text = "Bugun to'lash kerak"
					status_uz = "Bugun"
				elif days_left <= 3:
					status = "soon"
					status_text = f"{days_left} kundan keyin"
					status_uz = "Yaqinda"
				else:
					status = "upcoming"
					status_text = f"{days_left} kun qoldi"
					status_uz = "Kelgusi"

				next_payments[s.parent] = {
					"due_date": formatdate(s.due_date, "dd.MM.yyyy"),
					"amount": flt(s.payment_amount),
					"outstanding": flt(s.outstanding),
					"days_left": days_left,
					"status": status,
					"status_text": status_text,
					"status_uz": status_uz,
					"month_number": s.idx
				}

	except Exception as e:
		frappe.log_error(f"Error getting next payment batch: {e}")

	return next_payments


# ============================================================
# 7) KEYINGI TO'LOVLAR (BARCHA SHARTNOMALAR)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_upcoming_payments(customer_name):
	"""
	Customer ning barcha shartnomalar bo'yicha yaqin to'lovlarini ko'rsatish

	OPTIMIZED VERSION - bitta SQL query
	"""
	try:
		# Bitta optimallashtirilgan query
		upcoming_payments = frappe.db.sql("""
			SELECT
				ps.parent as contract_id,
				so.transaction_date as contract_date,
				ps.due_date,
				ps.payment_amount,
				ps.outstanding,
				ps.idx as month_number,
				DATEDIFF(ps.due_date, CURDATE()) as days_left
			FROM `tabPayment Schedule` ps
			INNER JOIN `tabSales Order` so ON so.name = ps.parent
			WHERE so.customer = %s
				AND so.docstatus = 1
				AND so.status != 'Cancelled'
				AND ps.outstanding > 0
			ORDER BY ps.due_date ASC
		""", (customer_name,), as_dict=True)

		# Har bir shartnoma uchun faqat birinchi to'lovni olish
		seen_contracts = set()
		payments_list = []

		for p in upcoming_payments:
			if p.contract_id not in seen_contracts:
				seen_contracts.add(p.contract_id)

				days_left = p.days_left or 0

				# Status aniqlash
				if days_left < 0:
					status = "overdue"
					status_text = f"{abs(days_left)} kun kechikkan"
					status_uz = "Kechikkan"
				elif days_left == 0:
					status = "today"
					status_text = "Bugun to'lash kerak"
					status_uz = "Bugun"
				elif days_left <= 3:
					status = "soon"
					status_text = f"{days_left} kundan keyin"
					status_uz = "Yaqinda"
				else:
					status = "upcoming"
					status_text = f"{days_left} kun qoldi"
					status_uz = "Kelgusi"

				payments_list.append({
					"contract_id": p.contract_id,
					"contract_date": formatdate(p.contract_date, "dd.MM.yyyy"),
					"due_date": formatdate(p.due_date, "dd.MM.yyyy"),
					"amount": flt(p.payment_amount),
					"outstanding": flt(p.outstanding),
					"days_left": days_left,
					"month_number": p.month_number,
					"status": status,
					"status_text": status_text,
					"status_uz": status_uz
				})

		return {
			"success": True,
			"payments": payments_list,
			"total_upcoming": len(payments_list)
		}

	except Exception as e:
		frappe.log_error(str(e), "Get Upcoming Payments Error")
		return {
			"success": False,
			"message": str(e)
		}


# ============================================================
# 8) TO'LOV JADVALI (BITTA SHARTNOMA UCHUN)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_payment_schedule(contract_id):
	"""
	Bitta shartnoma uchun to'liq to'lov jadvali

	Barcha oylik to'lovlar (to'langan va to'lanmagan)
	"""
	if not contract_id:
		return {
			"success": False,
			"message": "Shartnoma ID kiritilmagan"
		}

	try:
		# Payment Schedule ni to'g'ridan-to'g'ri SQL bilan olish
		schedules = frappe.db.sql("""
			SELECT
				idx as month_number,
				due_date,
				payment_amount,
				paid_amount,
				outstanding,
				DATEDIFF(due_date, CURDATE()) as days_left
			FROM `tabPayment Schedule`
			WHERE parent = %s
			ORDER BY idx ASC
		""", (contract_id,), as_dict=True)

		schedule_list = []

		for row in schedules:
			# To'lov holati
			if flt(row.outstanding) == 0:
				pay_status = "paid"
				pay_status_uz = "To'langan"
			elif flt(row.paid_amount) > 0:
				pay_status = "partial"
				pay_status_uz = "Qisman to'langan"
			else:
				pay_status = "unpaid"
				pay_status_uz = "To'lanmagan"

			# Kechikish tekshirish
			days_left = row.days_left or 0
			is_overdue = days_left < 0 and flt(row.outstanding) > 0

			schedule_list.append({
				"month": row.month_number,
				"due_date": formatdate(row.due_date, "dd.MM.yyyy"),
				"amount": flt(row.payment_amount),
				"paid": flt(row.paid_amount),
				"outstanding": flt(row.outstanding),
				"status": pay_status,
				"status_uz": pay_status_uz,
				"days_left": days_left,
				"is_overdue": is_overdue
			})

		return {
			"success": True,
			"contract_id": contract_id,
			"schedule": schedule_list,
			"total_months": len(schedule_list)
		}

	except Exception as e:
		frappe.log_error(str(e), "Payment Schedule Error")
		return {
			"success": False,
			"message": str(e)
		}


# ============================================================
# 9) TELEGRAM LINKING
# ============================================================

@frappe.whitelist(allow_guest=True)
def link_telegram_user(customer_id, telegram_chat_id):
	"""
	Customer bilan Telegram account ni bog'lash

	Odatda get_customer_by_id() avtomatik bog'laydi,
	bu qo'lda bog'lash uchun
	"""
	try:
		if not frappe.db.exists("Customer", customer_id):
			return {
				"success": False,
				"message": f"Customer topilmadi: {customer_id}"
			}

		doc = frappe.get_doc("Customer", customer_id)

		# Agar allaqachon bog'langan bo'lsa
		if doc.get("custom_telegram_id"):
			return {
				"success": True,
				"message": "Telegram allaqachon bog'langan",
				"already_linked": True
			}

		# Yangi bog'lash
		doc.custom_telegram_id = str(telegram_chat_id)
		doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.logger().info(
			f"✅ Manual Telegram link: {customer_id} -> {telegram_chat_id}"
		)

		return {
			"success": True,
			"message": "Telegram ID muvaffaqiyatli bog'landi",
			"already_linked": False
		}

	except Exception as e:
		frappe.log_error(str(e), "Telegram Link Error")
		return {
			"success": False,
			"message": str(e)
		}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def translate_status(status):
	"""Sales Order status ni o'zbekchaga tarjima qilish"""
	status_map = {
		"Draft": "Qoralama",
		"On Hold": "To'xtatilgan",
		"To Deliver and Bill": "Yetkazish va hisob",
		"To Bill": "Hisob qilish kerak",
		"To Deliver": "Yetkazish kerak",
		"Completed": "Yakunlangan",
		"Cancelled": "Bekor qilingan",
		"Closed": "Yopilgan"
	}
	return status_map.get(status, status)


# ============================================================
# TELEGRAM LOGIN - PASSPORT VA PHONE BILAN
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_by_passport(passport_series, telegram_chat_id=None):
	"""
	Passport orqali mijozni topish va Telegram bog'lash

	⭐ Bu ASOSIY login usuli - Customer passport ID bilan kiradi

	Args:
		passport_series (str): Passport seriya raqami (masalan: AB1234567)
		telegram_chat_id (str/int): Telegram chat ID (SHART - notification uchun!)

	Returns:
		dict: To'liq customer ma'lumotlari

	Login jarayoni:
	1. Customer Telegram botga kiradi
	2. Bot so'raydi: "Passport seriyangizni kiriting"
	3. Customer passport kiritadi
	4. Bot bu function ni chaqiradi (passport + telegram_chat_id)
	5. Function passport bo'yicha customer topadi
	6. Telegram chat ID ni customer ga saqlaydi
	7. Keyingi safar notification yuborish mumkin! 🔔
	"""
	if not passport_series:
		return {
			"success": False,
			"message": "Passport raqami kiritilmagan",
			"message_uz": "Passport seriyangizni kiriting",
			"message_ru": "Введите серию паспорта"
		}

	try:
		customer_list = frappe.db.get_all(
			"Customer",
			filters={"custom_passport_series": passport_series},
			fields=["name"],
			limit=1
		)

		if not customer_list:
			return {
				"success": False,
				"message": "Mijoz topilmadi",
				"message_uz": f"Passport {passport_series} bo'yicha mijoz topilmadi. Iltimos, tekshirib ko'ring.",
				"message_ru": f"Клиент с паспортом {passport_series} не найден. Проверьте данные."
			}

		# ✅ get_customer_by_id ga yo'naltirish (telegram_chat_id BILAN!)
		# Bu telegram_chat_id ni avtomatik saqlaydi
		return get_customer_by_id(customer_list[0].name, telegram_chat_id)

	except Exception as e:
		frappe.log_error(str(e), "Passport Search Error")
		return {
			"success": False,
			"message": f"Xatolik: {e}",
			"message_uz": "Tizim xatosi. Qaytadan urinib ko'ring.",
			"message_ru": "Системная ошибка. Попробуйте снова."
		}


@frappe.whitelist(allow_guest=True)
def get_customer_by_phone(phone, telegram_chat_id=None):
	"""
	Telefon orqali qidirish va Telegram bog'lash

	Alternative login usuli - telefon raqam bilan

	Args:
		phone (str): Telefon raqami (masalan: +998901234567)
		telegram_chat_id (str/int): Telegram chat ID (notification uchun)
	"""
	if not phone:
		return {
			"success": False,
			"message": "Telefon raqami kiritilmagan",
			"message_uz": "Telefon raqamingizni kiriting",
			"message_ru": "Введите номер телефона"
		}

	try:
		customer_list = frappe.db.get_all(
			"Customer",
			filters={"custom_phone_1": phone},
			fields=["name"],
			limit=1
		)

		if not customer_list:
			return {
				"success": False,
				"message": "Mijoz topilmadi",
				"message_uz": f"Telefon {phone} bo'yicha mijoz topilmadi.",
				"message_ru": f"Клиент с телефоном {phone} не найден."
			}

		# ✅ get_customer_by_id ga yo'naltirish (telegram_chat_id BILAN!)
		return get_customer_by_id(customer_list[0].name, telegram_chat_id)

	except Exception as e:
		frappe.log_error(str(e), "Phone Search Error")
		return {
			"success": False,
			"message": f"Xatolik: {e}",
			"message_uz": "Tizim xatosi. Qaytadan urinib ko'ring.",
			"message_ru": "Системная ошибка. Попробуйте снова."
		}


@frappe.whitelist(allow_guest=True)
def get_customer_contracts(customer_name):
	"""Oddiy format shartnomalar - eski API"""
	# Yangi optimized function ga yo'naltirish
	return get_customer_contracts_detailed(customer_name)


@frappe.whitelist(allow_guest=True)
def get_contract_schedule(contract_id):
	"""Eski format to'lov jadvali"""
	# Yangi optimized function ga yo'naltirish
	return get_payment_schedule(contract_id)


@frappe.whitelist(allow_guest=True)
def get_next_installment(customer_name):
	"""Eski format keyingi to'lovlar"""
	# Yangi optimized function ga yo'naltirish
	return get_upcoming_payments(customer_name)


@frappe.whitelist(allow_guest=True)
def get_payment_history(contract_id):
	"""
	To'lovlar tarixi (alohida endpoint)

	Bu Payment Entry dan to'g'ridan-to'g'ri oladi
	"""
	try:
		payments = frappe.db.sql("""
			SELECT
				name as payment_id,
				posting_date,
				paid_amount,
				mode_of_payment
			FROM `tabPayment Entry`
			WHERE custom_contract_reference = %s
				AND docstatus = 1
				AND payment_type = 'Receive'
			ORDER BY posting_date DESC
		""", (contract_id,), as_dict=True)

		for p in payments:
			p["date"] = formatdate(p["posting_date"], "dd.MM.yyyy")
			p["amount"] = flt(p["paid_amount"])
			p["method"] = p["mode_of_payment"] or "Naqd"

		return {
			"success": True,
			"payments": payments,
			"total_payments": len(payments)
		}

	except Exception as e:
		frappe.log_error(str(e), "Payment History Error")
		return {"success": False, "message": str(e)}


# ============================================================
# NOTIFICATION SYSTEM - ESLATMALAR UCHUN
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customers_needing_reminders(reminder_days=None):
	"""
	To'lov eslatmasi yuborish kerak bo'lgan customerlarni topish

	Bu function Telegram bot uchun - cron job yoki scheduled task orqali chaqiriladi

	Eslatma jadvali:
	- 5 kun oldin
	- 3 kun oldin
	- 1 kun oldin
	- O'sha kuni (0 kun)
	- 1 kun keyin (kechikkan)
	- 3 kun keyin (kechikkan)
	- 5 kun keyin (kechikkan)

	Args:
		reminder_days (int): Necha kun oldin/keyin eslatma kerak
		                     -5 = 5 kun keyin (kechikkan)
		                     0 = bugun
		                     +5 = 5 kun oldin

	Returns:
		dict: {
			"success": True,
			"reminders": [
				{
					"customer_id": "CUST-00001",
					"customer_name": "Ahmadjon Karimov",
					"telegram_chat_id": "123456789",
					"contract_id": "SAL-ORD-00001",
					"due_date": "15.11.2025",
					"payment_amount": 2500000,
					"days_left": 5,
					"reminder_type": "5_days_before"
				}
			]
		}
	"""
	try:
		# Agar reminder_days ko'rsatilmagan bo'lsa, barcha aktiv eslatmalarni qaytarish
		if reminder_days is None:
			reminder_days_list = [5, 3, 1, 0, -1, -3, -5]
		else:
			reminder_days_list = [int(reminder_days)]

		all_reminders = []

		for days in reminder_days_list:
			# SQL query - to'lov sanasi reminder_days ga teng bo'lgan customerlar
			reminders = frappe.db.sql("""
				SELECT
					c.name as customer_id,
					c.customer_name,
					c.custom_telegram_id as telegram_chat_id,
					c.custom_phone_1 as phone,
					so.name as contract_id,
					ps.due_date,
					ps.payment_amount,
					ps.outstanding,
					ps.idx as month_number,
					DATEDIFF(ps.due_date, CURDATE()) as days_left
				FROM `tabPayment Schedule` ps
				INNER JOIN `tabSales Order` so ON so.name = ps.parent
				INNER JOIN `tabCustomer` c ON c.name = so.customer
				WHERE ps.outstanding > 0
					AND so.docstatus = 1
					AND so.status != 'Cancelled'
					AND c.custom_telegram_id IS NOT NULL
					AND c.custom_telegram_id != ''
					AND DATEDIFF(ps.due_date, CURDATE()) = %s
				ORDER BY ps.due_date ASC
			""", (days,), as_dict=True)

			# Har bir shartnoma uchun faqat birinchi to'lanmagan to'lovni olish
			seen_contracts = set()

			for r in reminders:
				# Har bir shartnoma uchun faqat bitta eslatma
				if r.contract_id not in seen_contracts:
					seen_contracts.add(r.contract_id)

					days_left = r.days_left or 0

					# Reminder type aniqlash
					if days_left == 5:
						reminder_type = "5_days_before"
						reminder_text = "5 kundan keyin to'lov kuni!"
					elif days_left == 3:
						reminder_type = "3_days_before"
						reminder_text = "3 kundan keyin to'lov kuni!"
					elif days_left == 1:
						reminder_type = "1_day_before"
						reminder_text = "Ertaga to'lov kuni!"
					elif days_left == 0:
						reminder_type = "today"
						reminder_text = "BUGUN to'lov kuni!"
					elif days_left == -1:
						reminder_type = "1_day_overdue"
						reminder_text = "To'lov 1 kun kechikdi!"
					elif days_left == -3:
						reminder_type = "3_days_overdue"
						reminder_text = "To'lov 3 kun kechikdi!"
					elif days_left == -5:
						reminder_type = "5_days_overdue"
						reminder_text = "To'lov 5 kun kechikdi!"
					else:
						reminder_type = "other"
						reminder_text = f"{abs(days_left)} kun"

					all_reminders.append({
						"customer_id": r.customer_id,
						"customer_name": r.customer_name,
						"telegram_chat_id": r.telegram_chat_id,
						"phone": r.phone or "",
						"contract_id": r.contract_id,
						"due_date": formatdate(r.due_date, "dd.MM.yyyy"),
						"payment_amount": flt(r.payment_amount),
						"outstanding": flt(r.outstanding),
						"month_number": r.month_number,
						"days_left": days_left,
						"reminder_type": reminder_type,
						"reminder_text": reminder_text,
						"is_overdue": days_left < 0
					})

		return {
			"success": True,
			"reminders": all_reminders,
			"total_reminders": len(all_reminders)
		}

	except Exception as e:
		frappe.log_error(str(e), "Get Reminders Error")
		return {
			"success": False,
			"message": str(e)
		}


@frappe.whitelist(allow_guest=True)
def get_today_reminders():
	"""
	Bugun eslatma yuborish kerak bo'lgan customerlar

	Bu function har kuni 1 marta chaqiriladi (masalan, ertalab 9:00 da)
	"""
	return get_customers_needing_reminders(reminder_days=0)


@frappe.whitelist(allow_guest=True)
def get_overdue_customers():
	"""
	To'lovni kechiktirgan customerlar

	Kechikkan to'lovlar uchun eslatma (1, 3, 5 kun keyin)
	"""
	try:
		# Barcha kechikkan to'lovlarni olish
		overdue = frappe.db.sql("""
			SELECT
				c.name as customer_id,
				c.customer_name,
				c.custom_telegram_id as telegram_chat_id,
				c.custom_phone_1 as phone,
				so.name as contract_id,
				ps.due_date,
				ps.payment_amount,
				ps.outstanding,
				ps.idx as month_number,
				DATEDIFF(CURDATE(), ps.due_date) as days_overdue
			FROM `tabPayment Schedule` ps
			INNER JOIN `tabSales Order` so ON so.name = ps.parent
			INNER JOIN `tabCustomer` c ON c.name = so.customer
			WHERE ps.outstanding > 0
				AND so.docstatus = 1
				AND so.status != 'Cancelled'
				AND c.custom_telegram_id IS NOT NULL
				AND c.custom_telegram_id != ''
				AND ps.due_date < CURDATE()
			ORDER BY ps.due_date ASC
		""", as_dict=True)

		overdue_list = []
		seen_contracts = set()

		for r in overdue:
			# Har bir shartnoma uchun faqat birinchi kechikkan to'lov
			if r.contract_id not in seen_contracts:
				seen_contracts.add(r.contract_id)

				days_overdue = r.days_overdue or 0

				overdue_list.append({
					"customer_id": r.customer_id,
					"customer_name": r.customer_name,
					"telegram_chat_id": r.telegram_chat_id,
					"phone": r.phone or "",
					"contract_id": r.contract_id,
					"due_date": formatdate(r.due_date, "dd.MM.yyyy"),
					"payment_amount": flt(r.payment_amount),
					"outstanding": flt(r.outstanding),
					"month_number": r.month_number,
					"days_overdue": days_overdue,
					"overdue_text": f"{days_overdue} kun kechikdi"
				})

		return {
			"success": True,
			"overdue_customers": overdue_list,
			"total_overdue": len(overdue_list)
		}

	except Exception as e:
		frappe.log_error(str(e), "Get Overdue Customers Error")
		return {
			"success": False,
			"message": str(e)
		}
