from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QStackedWidget, QLabel, QPushButton, QFrame)
from PyQt6.QtCore import Qt
from src.ui.dashboard import Dashboard
from src.ui.taxpayers import TaxpayersTab
from src.ui.adjudication_wizard import AdjudicationWizard
from src.ui.reports import ReportsTab
from src.ui.pending_works import PendingWorksTab
from src.ui.settings_tab import SettingsTab
from src.ui.case_register import CaseRegister
from src.ui.gst_handbook import GSTHandbook
from src.ui.mail_merge import MailMergeTab
from src.ui.adjudication_landing import AdjudicationLanding
from src.ui.case_management import CaseManagement
from src.ui.case_initiation_wizard import CaseInitiationWizard
from src.ui.proceedings_workspace import ProceedingsWorkspace
from src.ui.template_management import TemplateManagement
from src.ui.developer.developer_console import DeveloperConsole
from src.ui.components.sidebar import Sidebar
from src.ui.styles import Styles, Theme

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("THE GST DESK - Department of Goods & Services Tax")
        self.setGeometry(100, 100, 1280, 720) # Optimized for standard laptop screens
        
        # Apply Global Stylesheet
        self.setStyleSheet(Styles.get_main_stylesheet())

        # Main Layout (Horizontal: Sidebar | Content)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QHBoxLayout(main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = Sidebar()
        self.sidebar.navigate_signal.connect(self.navigate_to)
        self.sidebar.action_signal.connect(self.handle_case_action)
        self.layout.addWidget(self.sidebar)

        # 2. Content Area (Stacked Widget)
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Initialize Tabs
        self.dashboard = Dashboard(self.navigate_to)
        self.taxpayers_tab = TaxpayersTab(self.go_home)
        
        # Adjudication Module (Sub-stack)
        self.adjudication_container = QWidget()
        self.adjudication_layout = QVBoxLayout(self.adjudication_container)
        self.adjudication_layout.setContentsMargins(0, 0, 0, 0)
        self.adjudication_stack = QStackedWidget()
        self.adjudication_layout.addWidget(self.adjudication_stack)
        
        self.adjudication_landing = AdjudicationLanding(self.handle_adjudication_nav)
        self.new_case_flow = CaseInitiationWizard(self.handle_adjudication_nav)
        self.proceedings_workspace = ProceedingsWorkspace(self.handle_adjudication_nav)
        self.case_management = CaseManagement(self.launch_wizard_with_case)
        
        # Old Wizard (Keeping for reference or legacy, but hidden from main flow)
        self.adjudication_wizard = AdjudicationWizard(lambda: self.handle_adjudication_nav("landing"))
        
        self.adjudication_stack.addWidget(self.adjudication_landing)     # Index 0
        self.adjudication_stack.addWidget(self.new_case_flow)            # Index 1
        self.adjudication_stack.addWidget(self.proceedings_workspace)    # Index 2
        self.adjudication_stack.addWidget(self.case_management)          # Index 3
        self.adjudication_stack.addWidget(self.adjudication_wizard)      # Index 4
        
        self.reports_tab = ReportsTab(self.go_home)
        self.pending_works_tab = PendingWorksTab(self.go_home, self.resume_case)
        self.case_register_tab = CaseRegister()
        self.gst_handbook_tab = GSTHandbook()
        self.mail_merge_tab = MailMergeTab()
        self.template_management_tab = TemplateManagement(self.go_home)
        self.developer_console_tab = DeveloperConsole()

        # Add screens to main stack
        self.stack.addWidget(self.dashboard)       # Index 0
        self.stack.addWidget(self.taxpayers_tab)   # Index 1
        self.stack.addWidget(self.adjudication_container) # Index 2 (Adjudication Module)
        self.stack.addWidget(self.reports_tab)     # Index 3
        self.stack.addWidget(self.pending_works_tab) # Index 4
        self.stack.addWidget(self.case_register_tab) # Index 5
        self.stack.addWidget(self.gst_handbook_tab) # Index 6
        self.stack.addWidget(self.mail_merge_tab)   # Index 7
        self.stack.addWidget(self.template_management_tab) # Index 8
        self.stack.addWidget(self.developer_console_tab) # Index 9
        
        # Scrutiny Module
        from src.ui.scrutiny_tab import ScrutinyTab
        self.scrutiny_tab = ScrutinyTab()
        self.stack.addWidget(self.scrutiny_tab) # Index 10
        
        # Settings Tab
        self.settings_tab = SettingsTab(self.go_home)
        self.stack.addWidget(self.settings_tab) # Index 11
        
        # Set initial state
        self.sidebar.set_active_btn(0)

    def navigate_to(self, index):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active_btn(index) # Sync sidebar state
        
        # If navigating to Adjudication (Index 2), ensure Landing Page is shown
        # unless we are already there?
        if index == 2:
            # If we are just clicking "Adjudication" from global menu, go to landing
            # But if we are coming back from a case, maybe we want to stay?
            # For now, let's default to landing if coming from global nav
            if self.sidebar.current_mode == "global":
                 self.adjudication_stack.setCurrentIndex(0)

    def handle_case_action(self, action):
        """Handle actions from Case Workflow Sidebar"""
        if self.stack.currentIndex() == 2 and self.adjudication_stack.currentIndex() == 2:
            # We are in Proceedings Workspace
            self.proceedings_workspace.handle_sidebar_action(action)

    def handle_adjudication_nav(self, target, data=None):
        """Navigate within the Adjudication sub-stack"""
        if target == "new_case":
            # self.adjudication_wizard.reset_form()
            self.adjudication_stack.setCurrentIndex(1) # New Case Flow
        elif target == "continue_case":
            self.adjudication_stack.setCurrentIndex(3) # Case Management
        elif target == "workspace":
            # data should be proceeding_id
            self.proceedings_workspace.load_proceeding(data)
            self.adjudication_stack.setCurrentIndex(2) # Workspace
            # Switch Sidebar to Case Mode
            self.sidebar.set_mode("case")
            self.sidebar.set_active_btn("summary") # Default to summary
        elif target == "landing":
            self.adjudication_stack.setCurrentIndex(0) # Landing
            self.sidebar.set_mode("global")

    def launch_wizard_with_case(self, mode, case_data):
        """Launch wizard pre-filled with case data"""
        if mode == "workspace" or (isinstance(case_data, dict) and case_data.get('source') == 'sqlite'):
             # Extract ID
             pid = case_data.get('id') if isinstance(case_data, dict) else case_data
             self.handle_adjudication_nav("workspace", pid)
             return

        # This is for legacy support or if we want to map old cases to new flow
        # For now, let's just use the old wizard if it's an old case, or try to adapt
        self.adjudication_wizard.load_case_data(case_data, mode)
        self.adjudication_stack.setCurrentIndex(4) # Show Old Wizard

    def go_home(self):
        self.navigate_to(0)
        # Refresh dashboard counts if needed
        # self.dashboard.refresh_counts()

    def resume_case(self, case_data):
        # Load data into wizard and switch to it
        self.adjudication_wizard.load_case_data(case_data)
        self.stack.setCurrentIndex(2) # Adjudication Container
        self.adjudication_stack.setCurrentIndex(4) # Wizard

