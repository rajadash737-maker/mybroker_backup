# Site Visit runtime secret operations

`SITE_VISIT_REFUND_ENCRYPTION_KEY` is required before the application can accept buyer UPI refund details or decrypt stored UPI values for Accounting. The value must be exactly 64 hexadecimal characters, representing 32 random bytes. Keep it separate from the OTP and other application keys.

## Provisioning

Generate the value in the deployment's approved secret manager and expose it to the backend process as `SITE_VISIT_REFUND_ENCRYPTION_KEY`. For local development, set it in an untracked environment file or process environment; do not commit it, put it in source control, or paste it into logs or tickets. The checked-in `.env.example` files contain placeholders only. No production key is included in this repository.

The deployment should validate the secret format before rollout. The application requires exactly 64 hexadecimal characters and validates the format before an encryption/decryption operation. With the key absent or malformed, `POST /site-visits/{booking_id}/refund-details` returns HTTP 503 with a safe message explaining that the booking remains cancelled and refund details are still required. The transaction is rolled back, the pending refund case remains intact, and no plaintext UPI is stored. To verify in an isolated environment, unset the variable and submit refund details for a test booking already cancelled after successful payment; confirm the 503 and that `buyer_upi_ciphertext` remains null. Do not perform this check against production data.

## Rotation

The current `v1:` ciphertext format uses one configured key and does not embed a key identifier. Replacing the key before re-encrypting existing records makes those records unreadable. Keep the old key securely available and do not rotate it by simply replacing the environment value.

Before rotation, deploy a reviewed one-time re-encryption procedure that can read using the old key and write each UPI value using the new key, verify all rows, and only then switch the runtime secret. Keep the old key in the secret manager, access-restricted and offline from normal runtime, until row counts and decryption checks pass and a recovery window expires. Pause refund-detail writes and Accounting decryption during the controlled operation. The repository does not currently provide a dual-key keyring or a production rotation command; rotation must wait until that procedure is implemented and rehearsed against an isolated database backup.

## Completion-code crypto configuration

The runtime reads these exact process/environment variable names:

- `SITE_VISIT_OTP_ENCRYPTION_KEY`: exactly 32 random bytes encoded as 64 hexadecimal characters. This is the AES-256-GCM encryption key used for the recoverable, encrypted completion code.
- `SITE_VISIT_OTP_HMAC_KEY`: at least 32 random bytes encoded as an even number of hexadecimal characters (minimum 64). This is the keyed HMAC verification key.

Both values must contain only hex characters: no quotes included in the value, spaces, tabs, or newlines. The two decoded keys must differ. Keep them stable: changing either key can make existing active encrypted codes unreadable or existing hashes unverifiable. Never generate replacement keys for an environment that may have existing Site Visit completion-code records.

`app/core/config.py` now loads `.env` from the backend project root (`Path(__file__).resolve().parents[2] / ".env"`) with `override=False`, so process-level secret-manager variables take precedence and Uvicorn's working directory does not select a different `.env`. Startup validation reports only invalid/missing variable names; it never logs values. The current local workspace `.env` has neither completion-code variable, and neither is set in the inspected process environment. No key values were read or printed. The app therefore starts with a configuration error log and completion-code operations remain unavailable until the correct existing keys are supplied.

The key validator rejects missing values, malformed hex, whitespace/newlines, wrong lengths, and keys that decode to the same bytes. It does not generate defaults. Completion-code ciphertext, HMAC algorithm, expiry, failed-attempt behavior, buyer-only retrieval, and existing database values are unchanged.

### Windows PowerShell: load existing keys and restart Uvicorn

Use the existing values from the environment's approved secret manager or from the administrator responsible for the running backend. Do not use newly generated keys for an environment with existing bookings. These commands prompt without echoing the values and set them only in this PowerShell process:

```powershell
Set-Location 'C:\MyBrokerr\mybroker_backend-main\mybroker_backend-main'

function Set-ProcessSecretFromPrompt([string]$VariableName) {
    $secureValue = Read-Host "Enter existing $VariableName" -AsSecureString
    $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
    try {
        $plainValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
        [Environment]::SetEnvironmentVariable($VariableName, $plainValue, 'Process')
    }
    finally {
        if ($secretPointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
        }
        $plainValue = $null
        $secureValue.Dispose()
    }
}

Set-ProcessSecretFromPrompt 'SITE_VISIT_OTP_ENCRYPTION_KEY'
Set-ProcessSecretFromPrompt 'SITE_VISIT_OTP_HMAC_KEY'

python -c "from app.site_visits.completion_code import completion_code_configuration_issues as check; issues = check(); print(('Invalid configuration: ' + ', '.join(issues)) if issues else 'Completion-code configuration is valid')"
```

Proceed only if validation says the configuration is valid. Stop the old server with `Ctrl+C`, then start it again **from this same PowerShell window** so Uvicorn inherits the process variables. Use your normal launch command, for example:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For a Windows service or deployment, configure the same exact names in its protected secret store/environment and restart that service. Process-scoped PowerShell variables do not persist after that shell exits. Do not paste key values into command history, tickets, logs, or committed `.env` files. The checked-in `.env.example` lists the names with empty values only.

### Isolated local development only

If an isolated local database has never stored completion-code hashes/ciphertext and no deployed environment shares its keys, create and protect two new independent values using a password manager or approved secret generator, then use the process-scoped prompts above. Do not point a fresh-key local process at an existing database until its key history is confirmed.
