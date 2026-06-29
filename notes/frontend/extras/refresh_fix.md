

### Frontend Bug :
scénario: l'app reste inactive +30 min (user est partie prendre une pause, travail,etc..). 
Puis l'user revient sur l'appli. 
error backend:
INFO:     127.0.0.1:39850 - "GET /api/v1/auth/me HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:39860 - "GET /api/v1/dashboard/summary HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:39894 - "GET /api/v1/auth/me HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:39900 - "GET /api/v1/dashboard/summary HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:39914 - "GET /api/v1/dashboard/summary HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:39920 - "GET /api/v1/jobs?page=1&page_size=25 HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:55060 - "GET /api/v1/jobs?page=1&page_size=25 HTTP/1.1" 401 Unauthorized
Fix contournement:
l'user est forcé de se déconnecter puis se reconnecter


---
### Process Explicaation

The user is describing a real issue: when the access token expires (after 30 minutes), the app keeps making API calls that return 401, but the user is stuck because:
1. The token is expired but still stored in localStorage
2. The auth guard thinks the user is authenticated (token exists)
3. But all API calls fail with 401
4. The only way out is manual logout

The fix needs to handle token expiration gracefully:
1. When any API call returns 401, automatically logout and redirect to login
2. Or try to refresh the token automatically

The simplest and most reliable fix: intercept 401 responses in the API client and force logout.

Let me update the `api/client.ts` to handle 401 by calling logout.

---
### Fix

Le token expire après 30 min mais l'app ne gère pas le 401. Je corrige dans l'API client : à la première 401, logout automatique + redirection.
```ts
if (res.status === 401 && token) {
  localStorage.removeItem("resq_access_token")
  localStorage.removeItem("resq_refresh_token")
  window.location.href = "/login"  // ← force logout + redirect
  throw new Error("Session expirée")
}
```
 ** _Correct/Fixed Comportement après 30 min d'inactivité_ :**
1. N'importe quel appel API reçoit un 401
2. Le token est effacé du localStorage
3. Redirection forcée vers `/login`
4. L'utilisateur arrive sur la page de connexion (plus aucun appel API ne tourne)
