import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getFirestore, connectFirestoreEmulator } from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyCmNzCO5qg8CpaWQr6_-ORJWMRGz6iuN5A",
  authDomain: "asuman-integral.firebaseapp.com",
  projectId: "asuman-integral",
  storageBucket: "asuman-integral.firebasestorage.app",
  messagingSenderId: "354658507685",
  appId: "1:354658507685:web:df02b803fd7eeb92aaa64c",
  measurementId: "G-GY1TWYBT81"
};

const app = initializeApp(firebaseConfig);

const auth = getAuth(app);
const db = getFirestore(app);

// --- YENİ EKLENEN KISIM ---
// Eğer uygulama localhost'ta çalışıyorsa, emülatörlere bağlan
if (window.location.hostname === "localhost") {
  console.log("Localhost'ta çalışıyor. Firestore emülatörüne bağlanılıyor...");
  // Port numarasını firebase.json dosyanızdaki ile eşleştirin
  connectFirestoreEmulator(db, 'localhost', 8082); 
}
// --- BİTTİ ---

export { auth, db };