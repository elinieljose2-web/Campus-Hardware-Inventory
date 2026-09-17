import tkinter as tk
import theme
import logger
import seed_db
from controllers.auth_controller import AuthController
from controllers.hardware_controller import HardwareController
import views.login_view as login_view
import views.student_view as student_view
import views.admin_view as admin_view


class MainApplication:
    PORTAL_GEOMETRY = "1100x720"

    def __init__(self):
        self.root = tk.Tk()
        
        # Disable window resizing
        self.root.resizable(False, False)
        
        theme.apply_global_theme(self.root)

        # Shared Controller Instances
        self.auth_controller = AuthController()
        self.hardware_controller = HardwareController()

        # Seed demo hardware data when the inventory is empty
        if not self.hardware_controller.get_all_hardware():
            seed_db.seed_database()
            self.hardware_controller = HardwareController()

        logger.logger.info("Application started")
        self.show_login_screen()

    def show_login_screen(self):
        self.clear_screen()
        self.root.title("NATIONAL UNIVERSITY-MANILA | Laboratory Portal")
        self.root.geometry(self.PORTAL_GEOMETRY)
        login_view.LoginWindow(self.root, self.auth_controller, self.on_login_success)

    def on_login_success(self, user):
        
        self.clear_screen()
        role = user.get("role", "STUDENT").upper()

        if role == "ADMIN":
            self.root.title("NATIONAL UNIVERSITY-MANILA | Admin Portal")
            self.root.geometry(self.PORTAL_GEOMETRY)
            admin_view.AdminDashboardWindow(self.root, user, self.hardware_controller, self.show_login_screen, self.auth_controller)
        else:
            self.root.title("NATIONAL UNIVERSITY-MANILA | Student Portal")
            self.root.geometry(self.PORTAL_GEOMETRY)
            student_view.StudentReservationWindow(self.root, user, self.hardware_controller, self.show_login_screen)

        self.root.update_idletasks()
        self.root.update()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MainApplication()
    app.run()