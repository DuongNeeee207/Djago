# HỆ THỐNG WEBSITE KHO & BÁN LẺ LINH KIỆN ĐIỆN THOẠI

Hệ thống được xây dựng bằng **Python Django** theo đúng mô hình:
1. **Khách hàng (User):** Xem danh mục linh kiện, tra cứu theo dòng máy, thêm giỏ hàng, đặt mua online (COD) và theo dõi đơn mua của mình.
2. **Quản trị viên (Admin):** Toàn quyền quản trị hệ thống, xem dashboard doanh thu/lãi gộp, quản lý kho linh kiện (giá vốn, vị trí kệ), nhập kho hàng từ nhà cung cấp, duyệt và xử lý đơn đặt hàng của khách.

---

## 1. Tài Khoản Thử Nghiệm (2 Vai Trò)

| Tài khoản | Mật khẩu | Vai trò | Quyền hạn trên hệ thống |
| :--- | :--- | :--- | :--- |
| **`admin`** | `admin123` | **Quản trị viên (Admin)** | **Toàn quyền:** Xem Dashboard doanh thu & lãi gộp, Quản lý kho, Thêm/sửa linh kiện, Giá vốn bình quân, Nhập hàng từ NCC, Duyệt đơn hàng khách đặt, Quản lý phân quyền, Django Admin |
| **`khachhang`** | `khachhang123` | **Khách hàng (User)** | Xem danh sách linh kiện đang bán, tra cứu tương thích máy, giỏ hàng, đặt mua online (COD), xem lịch sử "Đơn mua của tôi" |

---

## 2. Hướng Dẫn Khởi Động Dự Án

Mở terminal tại thư mục `d:\Du_An\QuanLi`:

```powershell
# 1. Kích hoạt môi trường ảo
..\venv\Scripts\activate

# 2. Khởi chạy server
python manage.py runserver
```

---

## 3. Các Đường Dẫn Chính

### Dành cho Khách hàng (User):
- **Cửa hàng / Trang chủ:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Tra cứu linh kiện theo đời máy:** [http://127.0.0.1:8000/compatibility/](http://127.0.0.1:8000/compatibility/)
- **Giỏ hàng của bạn:** [http://127.0.0.1:8000/cart/](http://127.0.0.1:8000/cart/)
- **Đơn mua của tôi:** [http://127.0.0.1:8000/my-orders/](http://127.0.0.1:8000/my-orders/)
- **Đăng nhập:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
- **Đăng ký mua hàng:** [http://127.0.0.1:8000/signup/](http://127.0.0.1:8000/signup/)

### Dành cho Quản trị viên (Admin):
- **Trung tâm Quản Trị (Admin Panel):** [http://127.0.0.1:8000/manage/](http://127.0.0.1:8000/manage/)
- **Quản lý đơn hàng khách đặt & Duyệt đơn:** [http://127.0.0.1:8000/manage/orders/](http://127.0.0.1:8000/manage/orders/)
- **Kho linh kiện & Quản lý giá vốn:** [http://127.0.0.1:8000/manage/products/](http://127.0.0.1:8000/manage/products/)
- **Nhập kho hàng từ NCC:** [http://127.0.0.1:8000/manage/receipts/](http://127.0.0.1:8000/manage/receipts/)
- **Phân quyền người dùng:** [http://127.0.0.1:8000/manage/users/](http://127.0.0.1:8000/manage/users/)
- **Django Admin gốc:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
