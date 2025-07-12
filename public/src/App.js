import React, { useState, useEffect } from 'react';
import { db } from './firebase';
import { collection, query, onSnapshot, orderBy, doc, updateDoc, where, arrayUnion, setDoc, getDoc } from 'firebase/firestore';
import { Users, BarChart2, Settings, MessageSquare, Send, Power, PowerOff } from 'lucide-react';

// --- Yardımcı Bileşenler ---

const Tag = ({ text, colorClass }) => (
  <span className={`px-2 py-1 text-xs font-medium rounded-full ${colorClass}`}>
    {text}
  </span>
);

const Sidebar = ({ activePanel, setActivePanel }) => {
  const navItems = [
    { id: 'operations', name: 'Operasyon Paneli', icon: MessageSquare },
    { id: 'sessions', name: 'Seans Yönetimi', icon: Users },
    { id: 'marketing', name: 'Pazarlama Analizi', icon: BarChart2 },
    { id: 'system_control', name: 'Sistem Kontrolü', icon: Settings },
  ];

  return (
    <div className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col shrink-0">
      <h1 className="text-2xl font-bold text-gray-800 mb-8">Asuman</h1>
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePanel(item.id)}
            className={`flex items-center gap-3 px-4 py-2 rounded-lg text-left transition-colors ${
              activePanel === item.id
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <item.icon size={20} />
            <span>{item.name}</span>
          </button>
        ))}
      </nav>
      <footer className="mt-auto text-center text-xs text-gray-400">
        <p>v0.1 - İntegral Yaşam</p>
      </footer>
    </div>
  );
};

// --- Panel Bileşenleri ---

const PlaceholderPanel = ({ title }) => (
  <div className="p-8">
    <h2 className="text-3xl font-bold text-gray-800 mb-4">{title}</h2>
    <div className="bg-white shadow-lg rounded-xl p-8 text-center">
      <p className="text-gray-500">Bu panel geliştirme aşamasındadır.</p>
    </div>
  </div>
);

const OperationsPanel = () => {
  const [danisanlar, setDanisanlar] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const q = query(collection(db, "danisanlar"), orderBy("ilkTemasTarihi", "desc"));
    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      setDanisanlar(querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  const handleStatusUpdate = async (id, yeniStatus) => {
    await updateDoc(doc(db, "danisanlar", id), { statu: yeniStatus });
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Veriler yükleniyor...</div>;

  return (
    <div className="p-8">
      <h2 className="text-3xl font-bold text-gray-800 mb-4">Operasyon Paneli</h2>
      <p className="text-md text-gray-500 mb-8">Takip ve Geri Kazanım Süreçleri</p>
      <div className="bg-white shadow-lg rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          {danisanlar.length === 0 ? (
            <p className="p-8 text-center text-gray-500">Henüz görüntülenecek danışan bulunmuyor.</p>
          ) : (
            <table className="min-w-full text-sm divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left font-semibold text-gray-600 uppercase tracking-wider">Kullanıcı Adı</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-600 uppercase tracking-wider">Durum</th>
                  <th className="px-6 py-3 text-left font-semibold text-gray-600 uppercase tracking-wider">Aksiyon</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {danisanlar.map((danisan) => (
                  <tr key={danisan.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium text-gray-900">{danisan.instagramKullaniciAdi}</td>
                    <td className="px-6 py-4"><Tag text={danisan.statu} colorClass="bg-green-100 text-green-800" /></td>
                    <td className="px-6 py-4">
                      <button onClick={() => handleStatusUpdate(danisan.id, 'randevu_alindi')} className="px-3 py-1 bg-blue-500 text-white text-xs font-semibold rounded-md hover:bg-blue-600">Randevu Ver</button>
                      <button onClick={() => handleStatusUpdate(danisan.id, 'takibe_alindi')} className="ml-2 px-3 py-1 bg-indigo-500 text-white text-xs font-semibold rounded-md hover:bg-indigo-600">Takibe Al</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

const SessionsPanel = () => {
    const [randevular, setRandevular] = useState([]);
    const [loading, setLoading] = useState(true);
    const [gorusmeNotu, setGorusmeNotu] = useState({});

    useEffect(() => {
        const q = query(collection(db, "danisanlar"), where("statu", "==", "randevu_alindi"), orderBy("ilkTemasTarihi", "desc"));
        const unsubscribe = onSnapshot(q, (querySnapshot) => {
            setRandevular(querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
            setLoading(false);
        });
        return () => unsubscribe();
    }, []);

    const handleNotGuncelle = async (id) => {
        const not = gorusmeNotu[id];
        if (!not || not.trim() === "") return;
        const danisanRef = doc(db, "danisanlar", id);
        await updateDoc(danisanRef, {
            gorusmeNotlari: arrayUnion({ not: not, tarih: new Date() }),
            statu: 'gorusme_tamamlandi'
        });
        setGorusmeNotu(prev => ({ ...prev, [id]: '' }));
    };

    if (loading) return <div className="p-8 text-center text-gray-500">Randevular yükleniyor...</div>;

    return (
        <div className="p-8">
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Seans Yönetimi</h2>
            <p className="text-md text-gray-500 mb-8">Görüşme bekleyen danışanlar ve seans notları.</p>
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {randevular.length === 0 ? (
                    <p className="col-span-full p-8 text-center text-gray-500">Görüşme bekleyen danışan bulunmuyor.</p>
                ) : (
                    randevular.map(danisan => (
                        <div key={danisan.id} className="bg-white shadow-lg rounded-xl p-6 flex flex-col">
                            <h3 className="font-bold text-xl text-gray-900 mb-2">{danisan.instagramKullaniciAdi}</h3>
                            <div className="mb-4 border-b pb-4">
                                <h4 className="font-semibold text-sm text-gray-600 mb-2">Danışan Brifingi</h4>
                                <p className="text-sm text-gray-700 mb-3">"{danisan.profilOzeti}"</p>
                                <div className="flex flex-wrap gap-2">{danisan.etiketler?.map((etiket, i) => <Tag key={i} text={etiket} colorClass="bg-gray-100 text-gray-800" />)}</div>
                            </div>
                            <div className="flex-grow">
                                <h4 className="font-semibold text-sm text-gray-600 mb-2">Görüşme Notu Ekle</h4>
                                <textarea className="w-full p-2 border rounded-md text-sm focus:ring-2 focus:ring-blue-500" rows="3" placeholder="Seans sonrası gözlemlerinizi buraya yazın..." value={gorusmeNotu[danisan.id] || ''} onChange={(e) => setGorusmeNotu(prev => ({ ...prev, [danisan.id]: e.target.value }))}></textarea>
                            </div>
                            <button onClick={() => handleNotGuncelle(danisan.id)} className="mt-4 w-full bg-green-500 text-white font-semibold py-2 rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-2"><Send size={16} />Notu Kaydet ve Tamamla</button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

// YENİ: Sistem Kontrol Paneli
const SystemControlPanel = () => {
    const [isSchedulerActive, setIsSchedulerActive] = useState(true);
    const [loading, setLoading] = useState(true);

    const controlDocRef = doc(db, "system_settings", "main_controls");

    useEffect(() => {
        // Firestore'dan ayarı gerçek zamanlı olarak dinle
        const unsubscribe = onSnapshot(controlDocRef, (doc) => {
            if (doc.exists()) {
                setIsSchedulerActive(doc.data().isSchedulerActive);
            } else {
                // Eğer ayar belgesi yoksa, varsayılan olarak 'true' ayarla
                setDoc(controlDocRef, { isSchedulerActive: true });
            }
            setLoading(false);
        });
        return () => unsubscribe();
    }, [controlDocRef]);

    const handleToggleScheduler = async () => {
        const newState = !isSchedulerActive;
        setLoading(true);
        try {
            await setDoc(controlDocRef, { isSchedulerActive: newState });
            setIsSchedulerActive(newState);
        } catch (error) {
            console.error("Sistem ayarı güncellenirken hata:", error);
        }
        setLoading(false);
    };

    return (
        <div className="p-8">
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Sistem Kontrolü</h2>
            <p className="text-md text-gray-500 mb-8">Arka plan servislerinin durumunu yönetin.</p>
            
            <div className="bg-white shadow-lg rounded-xl p-6 max-w-md">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="font-bold text-lg text-gray-800">Otomatik Mesaj Kontrolü</h3>
                        <p className="text-sm text-gray-500">
                            Bu servis aktifken, sistem her 5 dakikada bir yeni Instagram mesajlarını kontrol eder.
                        </p>
                    </div>
                    <button
                        onClick={handleToggleScheduler}
                        disabled={loading}
                        className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                            isSchedulerActive ? 'bg-green-500' : 'bg-gray-300'
                        }`}
                    >
                        <span
                            className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform duration-300 ${
                                isSchedulerActive ? 'translate-x-6' : 'translate-x-1'
                            }`}
                        />
                    </button>
                </div>
                {loading && <p className="text-xs text-gray-400 mt-2">Durum güncelleniyor...</p>}
                <div className={`mt-4 flex items-center gap-3 p-4 rounded-lg ${isSchedulerActive ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                    {isSchedulerActive ? <Power size={24} /> : <PowerOff size={24} />}
                    <div>
                        <p className="font-semibold">Servis Durumu: {isSchedulerActive ? 'AKTİF' : 'PASİF'}</p>
                        <p className="text-xs">{isSchedulerActive ? 'Kaynaklar kullanılıyor.' : 'Arka plan işlemleri durduruldu.'}</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Ana Uygulama ---

function App() {
  const [activePanel, setActivePanel] = useState('operations');

  const renderPanel = () => {
    switch (activePanel) {
      case 'operations':
        return <OperationsPanel />;
      case 'sessions':
        return <SessionsPanel />;
      case 'marketing':
        return <PlaceholderPanel title="Pazarlama Analizi Paneli" />;
      case 'system_control':
        return <SystemControlPanel />;
      default:
        return <OperationsPanel />;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar activePanel={activePanel} setActivePanel={setActivePanel} />
      <main className="flex-1 overflow-y-auto">
        {renderPanel()}
      </main>
    </div>
  );
}

export default App;
