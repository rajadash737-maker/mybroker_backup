package com.example.mybroker_admin.core.navigation

import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.example.mybroker_admin.feature.accounting.dashboard.AccountingDashboardScreen
import com.example.mybroker_admin.feature.accounting.propertyrefunds.PropertyBookingRefundsScreen
import com.example.mybroker_admin.feature.sitevisit.AccountingSiteVisitRefundsScreen
import com.example.mybroker_admin.feature.sitevisit.AccountingSiteVisitRefundDetailScreen
import com.example.mybroker_admin.feature.sitevisit.SiteVisitAuditScreen
import com.example.mybroker_admin.feature.sitevisit.SiteVisitAuditDetailScreen
import com.example.mybroker_admin.feature.admin.dashboard.presentation.AdminDashboardScreen
import com.example.mybroker_admin.feature.sitevisit.AdminSiteVisitsScreen
import com.example.mybroker_admin.feature.sitevisit.AdminSiteVisitBookingDetailScreen
import com.example.mybroker_admin.feature.sitevisit.FieldOfficerSiteVisitsScreen
import com.example.mybroker_admin.feature.sitevisit.FieldOfficerSiteVisitDetailScreen
import com.example.mybroker_admin.feature.auth.screen.LoginScreen
import com.example.mybroker_admin.feature.fieldofficer.dashboard.FieldDashboardScreen
import com.example.mybroker_admin.feature.superadmin.dashboard.SuperAdminDashboardScreen
import com.example.mybroker_admin.feature.superadmin.dashboard.SuperAdminRevenueScreen
import com.example.mybroker_admin.feature.superadmin.listings.screen.SuperAdminListingDetailScreen
import com.example.mybroker_admin.feature.superadmin.listings.screen.SuperAdminListingsScreen
import com.example.mybroker_admin.feature.superadmin.staffanalytics.screen.StaffAnalyticsScreen
import com.example.mybroker_admin.feature.superadmin.staff.screen.*
import com.example.mybroker_admin.feature.superadmin.staff.viewmodel.StaffViewModel
import androidx.compose.runtime.remember
import com.example.mybroker_admin.feature.admin.listings.presentation.AdminListingDetailScreen
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.mybroker_admin.feature.admin.listings.presentation.PendingListingsRoute
import androidx.compose.runtime.LaunchedEffect
import com.example.mybroker_admin.feature.admin.listings.AdminListingsViewModel
import android.widget.Toast
import androidx.compose.ui.platform.LocalContext
import com.example.mybroker_admin.feature.accounting.refunds.presentation.RefundListScreen
import com.example.mybroker_admin.feature.accounting.transactions.presentation.CompletedTransactionDetailRoute
import com.example.mybroker_admin.feature.accounting.transactions.presentation.CompletedTransactionsRoute
import com.example.mybroker_admin.feature.admin.approvals.presentation.FinalApprovalRoute
import com.example.mybroker_admin.feature.admin.cancel.presentation.CancelRefundScreen
import com.example.mybroker_admin.feature.admin.dashboard.presentation.AdminDashboardViewModel
import com.example.mybroker_admin.feature.admin.listings.presentation.AssignedListingsRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.BookedListingsRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.BookedListingDetailRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.RegistryPendingRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.LockedListingsRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.LiveListingsRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.SoldListingsRoute
import com.example.mybroker_admin.feature.admin.listings.presentation.RejectedListingsRoute
import com.example.mybroker_admin.feature.admin.payments.presentation.WebhookLogsRoute
import com.example.mybroker_admin.feature.fieldofficer.activecase.ActiveCaseDetailScreen
import com.example.mybroker_admin.feature.fieldofficer.available.AvailableCasesScreen
import com.example.mybroker_admin.feature.fieldofficer.dashboard.FieldDashboardViewModel
import com.example.mybroker_admin.feature.fieldofficer.sitevisit.FieldDocumentViewerScreen
import com.example.mybroker_admin.feature.fieldofficer.sitevisit.SiteVisitScreen
import com.example.mybroker_admin.feature.profile.ProfileScreen
import com.example.mybroker_admin.feature.profile.changepassword.ChangePasswordScreen
import com.example.mybroker_admin.feature.registry.screens.RegistryDashboardScreen
import com.example.mybroker_admin.feature.registry.screens.RegistryDetailScreen
import com.example.mybroker_admin.feature.superadmin.ratings.AdminRatingsScreen
import com.example.mybroker_admin.feature.superadmin.ratings.AdminRatingsViewModel
import com.example.mybroker_admin.feature.superadmin.settings.BannersScreen
import com.example.mybroker_admin.feature.superadmin.settings.ProcessingFeesScreen
import com.example.mybroker_admin.feature.superadmin.settings.SocialLinksScreen
import com.example.mybroker_admin.feature.notifications.NotificationsScreen
import com.example.mybroker_admin.notification.NotificationRoutes
import com.example.mybroker_admin.core.session.SessionManager
import com.example.mybroker_admin.data.remote.ApiClient
import com.example.mybroker_admin.notification.NotificationStore



@Composable
fun RootNavGraph(navController: NavHostController) {
    val siteVisitRefundRefreshKey = remember { mutableStateOf(0) }
    val siteVisitAuditRefreshKey = remember { mutableStateOf(0) }

    val startDestination = remember {
        when (SessionManager.dashboardKey) {
            "super_admin_dashboard" -> Routes.SUPER_ADMIN_DASHBOARD
            "admin_dashboard" -> Routes.ADMIN_DASHBOARD
            "field_officer_dashboard" -> Routes.FIELD_DASHBOARD
            "accounting_dashboard" -> Routes.ACCOUNTING_DASHBOARD
            else -> Routes.LOGIN
        }
    }

    NavHost(
        navController = navController,
        startDestination = startDestination
    ) {

        // ðŸ” LOGIN
        composable(Routes.LOGIN) {
            LoginScreen(
                onLoginSuccess = { dashboardKey ->

                    val targetRoute = when (dashboardKey) {
                        "super_admin_dashboard" -> Routes.SUPER_ADMIN_DASHBOARD
                        "admin_dashboard" -> Routes.ADMIN_DASHBOARD
                        "field_officer_dashboard" -> Routes.FIELD_DASHBOARD
                        "accounting_dashboard" -> Routes.ACCOUNTING_DASHBOARD
                        else -> Routes.LOGIN
                    }

                    if (targetRoute != Routes.LOGIN) {
                        navController.navigate(targetRoute) {
                            popUpTo(Routes.LOGIN) { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                }
            )
        }

        // ðŸ‘‘ SUPER ADMIN DASHBOARD
        composable(Routes.SUPER_ADMIN_DASHBOARD) {
            SuperAdminDashboardScreen(navController)
        }

        composable(Routes.SUPER_ADMIN_LISTINGS) {
            SuperAdminListingsScreen(navController)
        }

        composable(Routes.SUPER_ADMIN_SITE_VISIT_AUDIT) {
            SiteVisitAuditScreen(
                refreshKey = siteVisitAuditRefreshKey.value,
                onBack = { navController.popBackStack() },
                onOpenBooking = { bookingId -> navController.navigate(Routes.superAdminSiteVisitAuditDetail(bookingId)) }
            )
        }
        composable(
            route = Routes.SUPER_ADMIN_SITE_VISIT_AUDIT_DETAIL,
            arguments = listOf(navArgument("bookingId") { type = NavType.IntType })
        ) { entry ->
            val bookingId = entry.arguments?.getInt("bookingId") ?: return@composable
            SiteVisitAuditDetailScreen(
                bookingId = bookingId,
                onBack = { siteVisitAuditRefreshKey.value++; navController.popBackStack() }
            )
        }

        composable(
            route = Routes.SUPER_ADMIN_LISTING_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.IntType })
        ) { backStackEntry ->
            val listingId = backStackEntry.arguments?.getInt("id") ?: return@composable
            SuperAdminListingDetailScreen(
                navController = navController,
                listingId = listingId
            )
        }

        composable(Routes.STAFF_ANALYTICS) {
            StaffAnalyticsScreen(navController)
        }

        composable(Routes.SUPER_ADMIN_REVENUE) {
            SuperAdminRevenueScreen(navController)
        }

        composable(Routes.ADMIN_RATINGS) {
            val vm: AdminRatingsViewModel = viewModel()
            AdminRatingsScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.SOCIAL_LINKS) {
            SocialLinksScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.BANNERS) {
            BannersScreen(
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.PROCESSING_FEES) {
            ProcessingFeesScreen(
                onBack = { navController.popBackStack() }
            )
        }

        // ================================
        // ðŸ‘¥ STAFF MANAGEMENT FLOW
        // ================================

        composable(Routes.STAFF_MANAGEMENT) {
            val staffViewModel: StaffViewModel = viewModel()

            StaffListScreen(
                navController = navController,
                viewModel = staffViewModel
            )
        }

        composable(Routes.CREATE_STAFF) {
            val staffViewModel: StaffViewModel = viewModel()

            CreateStaffScreen(
                navController = navController,
                viewModel = staffViewModel
            )
        }

        // STAFF DETAIL
        composable(
            route = Routes.STAFF_DETAIL,
            arguments = listOf(navArgument("staffId") { type = NavType.IntType })
        ) { backStackEntry ->
            val staffId = backStackEntry.arguments?.getInt("staffId") ?: return@composable
            val parentEntry = remember(backStackEntry) {
                navController.getBackStackEntry(Routes.STAFF_MANAGEMENT)
            }
            val staffViewModel: StaffViewModel = viewModel(parentEntry)

            StaffDetailScreen(
                staffId = staffId,
                navController = navController,
                viewModel = staffViewModel
            )
        }



        // âœ EDIT STAFF
        composable(
            route = Routes.EDIT_STAFF,
            arguments = listOf(navArgument("staffId") { type = NavType.IntType })
        ) { backStackEntry ->
            val staffId = backStackEntry.arguments?.getInt("staffId") ?: return@composable
            EditStaffScreen(staffId = staffId, navController = navController, viewModel = viewModel())
        }

        // RESET PASSWORD
        composable(
            route = "reset_password/{staffId}",
        ) { backStackEntry ->

            val staffId = backStackEntry.arguments?.getString("staffId")?.toInt()

            ResetPasswordScreen(
                staffId = staffId!!,
                navController = navController
            )
        }



        // ================================
        // OTHER DASHBOARDS
        // ================================

        // profile pase

        composable(Routes.PROFILE) {
            val context = LocalContext.current
            ProfileScreen(
                onLogout = {
                    SessionManager.clear()
                    ApiClient.setAccessToken(null)
                    NotificationStore.clear(context)
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                onChangePassword = {
                    navController.navigate(Routes.CHANGE_PASSWORD)
                }
            )
        }

        composable(Routes.CHANGE_PASSWORD) {
            val context = LocalContext.current
            ChangePasswordScreen(
                onBack = { navController.popBackStack() },
                onLogout = {
                    SessionManager.clear()
                    ApiClient.setAccessToken(null)
                    NotificationStore.clear(context)
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                        launchSingleTop = true
                    }
                }
            )
        }


        // ===============================
        // ADMIN DASHBOARD
        // ===============================

        composable(Routes.SITE_VISITS) { listEntry ->
            val refreshKey by listEntry.savedStateHandle
                .getStateFlow("site_visit_queue_refresh", 0L)
                .collectAsStateWithLifecycle()
            AdminSiteVisitsScreen(
                onOpenBooking = { bookingId -> navController.navigate(Routes.siteVisitAdminDetail(bookingId)) },
                refreshKey = refreshKey
            )
        }
        composable(
            route = Routes.SITE_VISIT_ADMIN_DETAIL,
            arguments = listOf(navArgument("bookingId") { type = NavType.IntType })
        ) { entry ->
            val bookingId = entry.arguments?.getInt("bookingId") ?: return@composable
            AdminSiteVisitBookingDetailScreen(
                bookingId = bookingId,
                onBookingUpdated = {
                    navController.previousBackStackEntry?.savedStateHandle?.set("site_visit_queue_refresh", System.currentTimeMillis())
                },
                onBack = {
                    navController.previousBackStackEntry?.savedStateHandle?.set("site_visit_queue_refresh", System.currentTimeMillis())
                    navController.popBackStack()
                }
            )
        }
        composable(Routes.FIELD_SITE_VISITS) { listEntry ->
            val refreshKey by listEntry.savedStateHandle
                .getStateFlow("field_site_visit_queue_refresh", 0L)
                .collectAsStateWithLifecycle()
            FieldOfficerSiteVisitsScreen(
                onOpenBooking = { bookingId -> navController.navigate(Routes.fieldSiteVisitBookingDetail(bookingId)) },
                refreshKey = refreshKey
            )
        }
        composable(
            route = Routes.FIELD_SITE_VISIT_BOOKING_DETAIL,
            arguments = listOf(navArgument("bookingId") { type = NavType.IntType })
        ) { entry ->
            val bookingId = entry.arguments?.getInt("bookingId") ?: return@composable
            FieldOfficerSiteVisitDetailScreen(
                bookingId = bookingId,
                onBookingUpdated = {
                    navController.previousBackStackEntry?.savedStateHandle?.set(
                        "field_site_visit_queue_refresh", System.currentTimeMillis()
                    )
                },
                onBack = {
                    navController.previousBackStackEntry?.savedStateHandle?.set(
                        "field_site_visit_queue_refresh", System.currentTimeMillis()
                    )
                    navController.popBackStack()
                }
            )
        }

        composable(Routes.ADMIN_DASHBOARD) {
            val vm: AdminDashboardViewModel = viewModel()
            val stats = vm.stats.collectAsStateWithLifecycle().value
            val isLoading = vm.isLoading.collectAsStateWithLifecycle().value
            val context = LocalContext.current
            val notificationVersion = NotificationStore.version.collectAsStateWithLifecycle().value
            val unreadCount = remember(notificationVersion) {
                NotificationStore.unreadCount(context)
            }

            AdminDashboardScreen(
                stats = stats,
                isRefreshing = isLoading,
                unreadCount = unreadCount,
                onRefresh = { vm.loadStats() },
                onPendingClick = { navController.navigate(Routes.PENDING_LISTINGS) },
                onAssignedClick = { navController.navigate(Routes.ASSIGNED_LISTINGS) },
                onFieldVerifiedClick = { navController.navigate(Routes.FINAL_APPROVAL) },
                onLiveClick = { navController.navigate(Routes.LIVE_LISTINGS) },
                onLockedClick = { navController.navigate(Routes.LOCKED_LISTINGS) },
                onBookedClick = { navController.navigate(Routes.BOOKED_LISTINGS) },
                onSoldClick = { navController.navigate(Routes.SOLD_LISTINGS) },
                onRegistryPendingClick = { navController.navigate(Routes.REGISTRY_PENDING) },
                onRejectedClick = { navController.navigate(Routes.REJECTED_LISTINGS) },
                onCancelRefundClick = {
                    navController.navigate(Routes.ADMIN_CANCEL_REFUND)
                },
                onProfileClick = { navController.navigate(Routes.PROFILE) },
                onNotificationsClick = { navController.navigate(Routes.NOTIFICATIONS) },
                onSiteVisitsClick = { navController.navigate(Routes.SITE_VISITS) }
            )
        }



        //
        //=====PENDING LISTING ========
        //
        composable(Routes.PENDING_LISTINGS) {
            PendingListingsRoute(
                onListingClick = { listingId ->
                    navController.navigate("${Routes.ADMIN_LISTING_DETAIL}/$listingId")
                }
            )
        }

        //
        //===== LISTING DETAIL ========
        //

        composable("${Routes.ADMIN_LISTING_DETAIL}/{listingId}") { backStackEntry ->
            val listingId = backStackEntry.arguments
                ?.getString("listingId")
                ?.toIntOrNull()
                ?: return@composable

            val vm: AdminListingsViewModel = viewModel()
            val context = LocalContext.current

            LaunchedEffect(listingId) {
                vm.loadDetail(listingId)
            }

            val detail = vm.detail.collectAsStateWithLifecycle().value
            val isLoading = vm.isLoading.collectAsStateWithLifecycle().value
            val errorMessage = vm.errorMessage.collectAsStateWithLifecycle().value
            val rejectReason = vm.rejectReason.collectAsStateWithLifecycle().value
            val actionMessage = vm.actionMessage.collectAsStateWithLifecycle().value

            LaunchedEffect(actionMessage) {
                actionMessage?.let { msg ->
                    Toast.makeText(context, msg, Toast.LENGTH_SHORT).show()
                    vm.clearActionMessage()
                    navController.popBackStack()
                }
            }

            AdminListingDetailScreen(
                detail = detail,
                isLoading = isLoading,
                errorMessage = errorMessage,
                rejectReason = rejectReason,
                onRejectReasonChange = vm::onRejectReasonChange,
                onReject = {
                    vm.reject(listingId, rejectReason)
                },
                onForwardToField = {
                    vm.approve(listingId)
                }
            )
        }

        //
        //===== ASSIGNED LISTINGS ========
        //




        composable(Routes.ASSIGNED_LISTINGS) {
            AssignedListingsRoute()
        }

        //
        //===== FINAL APPROVAL ========
        //


        composable(Routes.FINAL_APPROVAL) {
            FinalApprovalRoute()
        }

        //
        //===== FINAL APPROVAL ========
        //


        composable(Routes.ADMIN_CANCEL_REFUND) {
            CancelRefundScreen()
        }

        //
        //===== FINAL APPROVAL ========
        //

        composable(Routes.LOCKED_LISTINGS) {
            LockedListingsRoute(
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.LIVE_LISTINGS) {
            LiveListingsRoute(
                onListingClick = { listingId ->
                    navController.navigate("${Routes.ADMIN_LISTING_DETAIL}/$listingId")
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.BOOKED_LISTINGS) { listEntry ->
            val refreshKey by listEntry.savedStateHandle
                .getStateFlow("booked_listings_refresh", 0L)
                .collectAsStateWithLifecycle()
            BookedListingsRoute(
                onListingClick = { listingId ->
                    navController.navigate(Routes.bookedListingDetail(listingId))
                },
                onBack = { navController.popBackStack() },
                refreshKey = refreshKey
            )
        }

        composable(Routes.SOLD_LISTINGS) {
            SoldListingsRoute(
                onListingClick = { listingId ->
                    navController.navigate(Routes.soldListingDetail(listingId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.REGISTRY_PENDING) {
            RegistryPendingRoute(
                onListingClick = { listingId ->
                    navController.navigate(Routes.bookedListingDetail(listingId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.REJECTED_LISTINGS) {
            RejectedListingsRoute(
                onListingClick = { listingId ->
                    navController.navigate("${Routes.ADMIN_LISTING_DETAIL}/$listingId")
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.NOTIFICATIONS) {
            NotificationsScreen(
                onBack = { navController.popBackStack() },
                onNotificationClick = { item ->
                    val route = NotificationRoutes.routeForNotification(
                        type = item.type,
                        referenceId = item.propertyId,
                        role = SessionManager.currentUserRole
                    )
                    if (route != null) {
                        navController.navigate(route) {
                            launchSingleTop = true
                        }
                    }
                }
            )
        }

        composable(Routes.WEBHOOK_LOGS) {
            WebhookLogsRoute(
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.BOOKED_LISTING_DETAIL,
            arguments = listOf(navArgument("listingId") { type = NavType.IntType })
        ) { backStackEntry ->
            val listingId = backStackEntry.arguments?.getInt("listingId") ?: return@composable
            BookedListingDetailRoute(
                listingId = listingId,
                onBack = { navController.popBackStack() },
                onCancellationCompleted = {
                    navController.previousBackStackEntry?.savedStateHandle?.set(
                        "booked_listings_refresh", System.currentTimeMillis()
                    )
                },
                onViewDocument = { url ->
                    navController.navigate(
                        Routes.fieldDocumentViewer(url, Routes.bookedListingDetail(listingId))
                    )
                }
            )
        }

        composable(
            route = Routes.SOLD_LISTING_DETAIL,
            arguments = listOf(navArgument("listingId") { type = NavType.IntType })
        ) { backStackEntry ->
            val listingId = backStackEntry.arguments?.getInt("listingId") ?: return@composable
            BookedListingDetailRoute(
                listingId = listingId,
                onBack = { navController.popBackStack() },
                onViewDocument = { url ->
                    navController.navigate(
                        Routes.fieldDocumentViewer(url, Routes.soldListingDetail(listingId))
                    )
                },
                readOnly = true
            )
        }

        // ===============================
        // REGISTRY ASSIGNMENT FLOW
        // ===============================

        composable(Routes.REGISTRY_DASHBOARD) {
            RegistryDashboardScreen(navController = navController)
        }

        composable(
            route = Routes.REGISTRY_DETAIL,
            arguments = listOf(navArgument("assignmentId") { type = NavType.StringType })
        ) { backStackEntry ->
            val assignmentId = backStackEntry.arguments?.getString("assignmentId") ?: return@composable
            RegistryDetailScreen(
                navController = navController,
                assignmentId = assignmentId
            )
        }




        // ===============================
        // ðŸš“ FIELD OFFICER FLOW
        // ===============================

        //
        //===== FIELD DASHBOARD ========
        //

        composable(Routes.FIELD_DASHBOARD) { backStackEntry ->

            val parentEntry = remember(backStackEntry) {
                navController.getBackStackEntry(Routes.FIELD_DASHBOARD)
            }

            val fieldViewModel: FieldDashboardViewModel = viewModel(parentEntry)

            FieldDashboardScreen(
                navController = navController,
                viewModel = fieldViewModel
            )
        }

        //
        //===== FIELD AVAILABLE CASES ========
        //

        composable(Routes.FIELD_AVAILABLE) { backStackEntry ->

            val parentEntry = remember(backStackEntry) {
                navController.getBackStackEntry(Routes.FIELD_DASHBOARD)
            }

            val fieldViewModel: FieldDashboardViewModel = viewModel(parentEntry)

            AvailableCasesScreen(
                navController = navController,
                viewModel = fieldViewModel
            )
        }

        //
        //===== FIELD ACTIVE CASE ========
        //

        composable(Routes.FIELD_ACTIVE_DETAIL) { backStackEntry ->

            val parentEntry = remember(backStackEntry) {
                navController.getBackStackEntry(Routes.FIELD_DASHBOARD)
            }

            val fieldViewModel: FieldDashboardViewModel = viewModel(parentEntry)

            ActiveCaseDetailScreen(
                navController = navController,
                viewModel = fieldViewModel
            )
        }

        //
        //===== FIELD SITE VISIT ========
        //

        composable(
            route = Routes.FIELD_SITE_VISIT,
            arguments = listOf(navArgument("requestId") { type = NavType.IntType })
        ) { backStackEntry ->
            val requestId = backStackEntry.arguments?.getInt("requestId") ?: return@composable

            SiteVisitScreen(
                navController = navController,
                requestId = requestId
            )
        }

        // NavGraph
        composable(
            route = Routes.FIELD_DOCUMENT_VIEWER,
            arguments = listOf(
                navArgument("docUrl") { type = NavType.StringType },
                navArgument("returnTo") { type = NavType.StringType }
            )
        ) { backStackEntry ->
            val encodedDocUrl = backStackEntry.arguments?.getString("docUrl").orEmpty()
            val encodedReturnTo = backStackEntry.arguments?.getString("returnTo").orEmpty()

            val docUrl = Uri.decode(encodedDocUrl)
            val returnTo = Uri.decode(encodedReturnTo)

            FieldDocumentViewerScreen(
                navController = navController,
                docUrl = docUrl,
                returnTo = returnTo
            )
        }






        // ===============================
        // ðŸš“ ACCOUNTING
        // ===============================


        //
        //===== ðŸ’° ACCOUNTING DASHBOARD ========
        //


        composable(Routes.ACCOUNTING_DASHBOARD) {
            AccountingDashboardScreen(navController = navController)
        }


        //
        //===== ðŸ’° ACCOUNTING REFUND LIST ========
        //


        composable(Routes.ACCOUNTING_REFUND_LIST) {
            RefundListScreen()
        }

        composable(Routes.ACCOUNTING_PROPERTY_BOOKING_REFUNDS) {
            PropertyBookingRefundsScreen(onBack = { navController.popBackStack() })
        }

        composable(Routes.ACCOUNTING_SITE_VISIT_REFUNDS) {
            AccountingSiteVisitRefundsScreen(
                refreshKey = siteVisitRefundRefreshKey.value,
                onBack = { navController.popBackStack() },
                onRefundClick = { bookingId -> navController.navigate(Routes.accountingSiteVisitRefundDetail(bookingId)) }
            )
        }
        composable(
            route = Routes.ACCOUNTING_SITE_VISIT_REFUND_DETAIL,
            arguments = listOf(navArgument("bookingId") { type = NavType.IntType })
        ) { entry ->
            val bookingId = entry.arguments?.getInt("bookingId") ?: return@composable
            AccountingSiteVisitRefundDetailScreen(
                bookingId = bookingId,
                onBack = { siteVisitRefundRefreshKey.value++; navController.popBackStack() }
            )
        }

        composable(Routes.ACCOUNTING_COMPLETED_TRANSACTIONS) {
            CompletedTransactionsRoute(
                onTransactionClick = { listingId ->
                    navController.navigate(Routes.accountingTransactionDetail(listingId))
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.ACCOUNTING_TRANSACTION_DETAIL,
            arguments = listOf(navArgument("listingId") { type = NavType.StringType })
        ) { backStackEntry ->
            val listingId = backStackEntry.arguments?.getString("listingId") ?: return@composable
            CompletedTransactionDetailRoute(
                listingId = listingId,
                onBack = { navController.popBackStack() }
            )
        }


    }
}
