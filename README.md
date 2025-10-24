### Cash Flow Management

USD-only cash and installment management for ERPNext

---

## 📖 O'zbekcha Ko'rsatma

Sheriklar uchun qisqa boshlash: [QUICKSTART_UZ.md](./QUICKSTART_UZ.md)  
To'liq o'rnatish bo'yicha ko'rsatma: [INSTALL_GUIDE_UZ.md](./INSTALL_GUIDE_UZ.md)

---

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench --site YOUR_SITE install-app cash_flow_app
```

**Important:** After installation, you need to import fixtures to apply all customizations:

```bash
bench --site YOUR_SITE migrate
```

This will automatically import:
- Custom Fields for ERPNext doctypes (Item, Customer, Supplier, Payment Entry, Sales Order, etc.)
- Property Setters (hidden fields and other customizations)
- Counterparty Categories
- Custom Modes of Payment (Naqd, Terminal/Click)

### For Developers

If you make changes to ERPNext doctypes (add custom fields, hide fields, etc.), export fixtures:

```bash
bench --site YOUR_SITE export-fixtures
```

Then commit the updated fixture files to git.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/cash_flow_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
