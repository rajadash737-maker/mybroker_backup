package com.example.myapplication.auth

import android.app.Activity
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.exceptions.NoCredentialException
import com.example.myapplication.BuildConfig
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import kotlinx.coroutines.CancellationException

sealed interface GoogleSignInResult {
    data class Success(val idToken: String) : GoogleSignInResult
    data object Cancelled : GoogleSignInResult
    data object NoGoogleAccount : GoogleSignInResult
    data class Failure(val message: String) : GoogleSignInResult
}

/** Acquires a Google ID token for exchange with the MyBrokerr backend. */
class GoogleSignInCoordinator {
    suspend fun getIdToken(activity: Activity): GoogleSignInResult {
        val webClientId = BuildConfig.GOOGLE_WEB_CLIENT_ID.takeIf(String::isNotBlank)
            ?: return GoogleSignInResult.Failure(
                "Google Sign-In is not configured. Add GOOGLE_WEB_CLIENT_ID to local.properties."
            )

        return try {
            val googleIdOption = GetGoogleIdOption.Builder()
                .setFilterByAuthorizedAccounts(false)
                .setServerClientId(webClientId)
                .build()
            val request = GetCredentialRequest.Builder()
                .addCredentialOption(googleIdOption)
                .build()
            val response = CredentialManager.create(activity).getCredential(activity, request)
            val credential = response.credential
            if (credential !is androidx.credentials.CustomCredential ||
                credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
            ) {
                return GoogleSignInResult.Failure("Google did not return a supported sign-in credential.")
            }
            val idToken = GoogleIdTokenCredential.createFrom(credential.data).idToken
            if (idToken.isBlank()) {
                GoogleSignInResult.Failure("Google returned an empty ID token. Please try again.")
            } else {
                GoogleSignInResult.Success(idToken)
            }
        } catch (_: GetCredentialCancellationException) {
            GoogleSignInResult.Cancelled
        } catch (_: NoCredentialException) {
            GoogleSignInResult.NoGoogleAccount
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (error: GetCredentialException) {
            GoogleSignInResult.Failure(error.message ?: "Unable to start Google sign-in. Please try again.")
        } catch (_: Exception) {
            GoogleSignInResult.Failure("Google sign-in could not be completed. Please try again.")
        }
    }
}
