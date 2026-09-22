// تهيئة Firebase — تسجيل الدخول بحساب Google فقط (لا Analytics، غير
// لازم لهالغرض ويزيد حجم الحزمة). قيم firebaseConfig ليست سرّية — مصمَّمة
// لتكون بكود العميل، الأمان الحقيقي بقواعد Firebase + تحقّق التوكن بالخادم.
import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider, signInWithPopup } from 'firebase/auth'

const firebaseConfig = {
  apiKey: 'AIzaSyBxj-jCyWSDgaY3n8Sb8Yuoh7nuCPXxCJc',
  authDomain: 'qaffel-50b29.firebaseapp.com',
  projectId: 'qaffel-50b29',
  storageBucket: 'qaffel-50b29.firebasestorage.app',
  messagingSenderId: '132476246339',
  appId: '1:132476246339:web:6256ac901f444bd595b7f6',
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
const googleProvider = new GoogleAuthProvider()

// يفتح نافذة اختيار حساب Google، ويُرجع Firebase ID token (JWT) — هذا هو
// الشيء الوحيد اللي يُرسَل للخادم؛ الخادم يتحقق منه بنفسه عبر Firebase
// Admin SDK، لا يُوثَق بأي بيانات مستخدم تُرسَل مباشرة من المتصفح.
export async function signInWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider)
  const idToken = await result.user.getIdToken()
  return idToken
}
