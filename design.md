# تصميم هيكل التطبيق الجديد

## 1. نقاط النهاية (API Endpoints) المطلوبة

### Authentication & Users
- `POST /api/auth/login` - تسجيل الدخول
- `POST /api/auth/logout` - تسجيل الخروج
- `GET /api/auth/me` - الحصول على معلومات المستخدم الحالي
- `GET /api/users` - عرض جميع المستخدمين (للمشرفين فقط)
- `POST /api/users` - إضافة مستخدم جديد (للمشرفين فقط)
- `PUT /api/users/{id}` - تعديل مستخدم (للمشرفين فقط)
- `DELETE /api/users/{id}` - حذف مستخدم (للمشرفين فقط)

### Tasks
- `GET /api/tasks` - عرض جميع المهام (مع إمكانية التصفية والبحث)
- `POST /api/tasks` - إضافة مهمة جديدة
- `GET /api/tasks/{id}` - عرض تفاصيل مهمة محددة
- `PUT /api/tasks/{id}` - تعديل مهمة
- `DELETE /api/tasks/{id}` - حذف مهمة

### Notifications
- `GET /api/notifications` - عرض الإشعارات للمستخدم الحالي
- `PUT /api/notifications/{id}/read` - تمييز إشعار كمقروء
- `DELETE /api/notifications/read` - حذف جميع الإشعارات المقروءة
- `GET /api/notifications/count` - عدد الإشعارات غير المقروءة

### Reports & Statistics
- `GET /api/reports/tasks-summary` - تقرير ملخص المهام
- `GET /api/reports/user-activity` - تقرير نشاط المستخدمين
- `GET /api/stats/dashboard` - إحصائيات لوحة التحكم
- `GET /api/stats/tasks-by-status` - إحصائيات المهام حسب الحالة
- `GET /api/stats/tasks-by-priority` - إحصائيات المهام حسب الأولوية

### Settings
- `GET /api/settings` - الحصول على الإعدادات الحالية
- `PUT /api/settings` - تحديث الإعدادات

## 2. نموذج قاعدة البيانات (Database Schema)

### جدول المستخدمين (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user', -- 'admin' or 'user'
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### جدول المهام (tasks)
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    assigned_to INTEGER,
    created_by INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'on_hold'
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### جدول الإشعارات (notifications)
```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'task_assigned', 'task_due_soon', 'task_overdue'
    is_read BOOLEAN DEFAULT 0,
    related_task_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (related_task_id) REFERENCES tasks(id)
);
```

### جدول الإعدادات (settings)
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 3. هيكل مجلدات المشروع

```
crm-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   ├── notification.py
│   │   │   └── setting.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── tasks.py
│   │   │   ├── notifications.py
│   │   │   ├── reports.py
│   │   │   └── settings.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── database.py
│   │   │   └── helpers.py
│   │   └── config.py
│   ├── migrations/
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── assets/
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   ├── components.css
│   │   │   └── themes.css
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── api.js
│   │   │   ├── auth.js
│   │   │   ├── tasks.js
│   │   │   ├── notifications.js
│   │   │   └── utils.js
│   │   └── images/
│   ├── pages/
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── tasks.html
│   │   ├── notifications.html
│   │   ├── reports.html
│   │   └── settings.html
│   └── index.html
└── README.md
```

## 4. المكونات الرئيسية للواجهة الأمامية

### 1. صفحة تسجيل الدخول (Login Page)
- نموذج تسجيل الدخول مع حقول اسم المستخدم وكلمة المرور
- زر تسجيل الدخول
- رسائل الخطأ والنجاح
- دعم اللغتين العربية والإنجليزية

### 2. لوحة التحكم الرئيسية (Dashboard)
- شريط التنقل العلوي مع القوائم
- بطاقات الإحصائيات السريعة (عدد المهام المعلقة، المكتملة، المتأخرة)
- قائمة المهام الحديثة
- منطقة الإشعارات

### 3. شاشة إدارة المهام (Tasks Management)
- جدول عرض المهام مع إمكانية التصفية والبحث
- أزرار إضافة، تعديل، وحذف المهام
- نموذج إضافة/تعديل المهام (Modal)
- فلاتر حسب الحالة، الأولوية، والمستخدم المسند إليه

### 4. شاشة الإشعارات (Notifications)
- قائمة الإشعارات مع إمكانية تمييزها كمقروءة
- أزرار تمييز الكل كمقروء وحذف المقروءة
- عداد الإشعارات في شريط التنقل

### 5. شاشة التقارير والإحصائيات (Reports & Statistics)
- مخططات بيانية للإحصائيات (Charts)
- أزرار تصدير التقارير
- فلاتر زمنية للتقارير

### 6. شاشة الإعدادات (Settings)
- تغيير اللغة
- تغيير السمة (فاتح/داكن)
- تغيير اسم الشركة
- إعدادات المستخدم

## 5. تصميم الواجهات (Wireframes/Mockups)

### تخطيط عام للصفحات:
```
+--------------------------------------------------+
|  Header (Logo, Navigation, User Menu, Notifications) |
+--------------------------------------------------+
|                                                  |
|  Main Content Area                               |
|  (يتغير حسب الصفحة المحددة)                      |
|                                                  |
|                                                  |
+--------------------------------------------------+
|  Footer (Copyright, Links)                       |
+--------------------------------------------------+
```

### لوحة التحكم الرئيسية:
```
+--------------------------------------------------+
|  Header                                          |
+--------------------------------------------------+
|  Welcome Message                                 |
|                                                  |
|  +------------+ +------------+ +------------+    |
|  | Pending    | | Completed  | | Overdue    |    |
|  | Tasks: 15  | | Tasks: 23  | | Tasks: 3   |    |
|  +------------+ +------------+ +------------+    |
|                                                  |
|  Recent Tasks                                    |
|  +--------------------------------------------+  |
|  | Task 1 | Status | Priority | Due Date     |  |
|  | Task 2 | Status | Priority | Due Date     |  |
|  | Task 3 | Status | Priority | Due Date     |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
```

### شاشة المهام:
```
+--------------------------------------------------+
|  Header                                          |
+--------------------------------------------------+
|  Filters: [Status ▼] [Priority ▼] [User ▼]      |
|  Search: [____________] [Search] [Reset]         |
|  [Add Task] [Edit] [Delete] [Refresh]            |
|                                                  |
|  +--------------------------------------------+  |
|  | ID | Title | Assigned | Status | Priority |  |
|  |----|-------|----------|--------|----------|  |
|  | 1  | Task1 | User1    | Pending| High     |  |
|  | 2  | Task2 | User2    | Done   | Medium   |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
```

هذا التصميم يوفر أساسًا قويًا لتطبيق ويب حديث ومتجاوب يحافظ على جميع وظائف التطبيق الأصلي مع تحسينات في تجربة المستخدم وقابلية الوصول.

