package com.example.myapplication.ui.feature

sealed class Screen(val route: String) {
    data object Home : Screen("home")
    data object Notifications : Screen("notifications")
    data object Profile : Screen("profile")
    data object Explore : Screen("explore")
    data object Wishlist : Screen("wishlist")
    data object Transactions : Screen("transactions")
    data object PropertyDetail : Screen("property/{id}")
}
