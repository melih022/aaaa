#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.

HELP_1 = """✅**<u>Sadece Gruptaki Adminler İçin Komutlar:</u>**✅

➥ /durdur - Akışı duraklatır.
➥ /devam - Akışı devam ettirir.
➥ /son - Akışı Sonlandırır.
➥ /atla - Diğer parça ya atlar.
✦ atla komutu aynı zamanda sıraya aldığınız istediğiniz parçaya atlar.( Örnek : /atla 3 -  3. Parçaya atlar )
➥ /ileri - Oynatılan parçayı ileri alır.
✦(örneğin: /ileri 30 - parçayı 30 saniye ileri alır)
➥  /gerial - Oynatılan parçayı geri alır.
✦(örneğin: /gerial 30 - parçayı 30 saniye geriye alır)
➥ /karistir - Sıraya alınan Parçaları karışık oynatır.
➥ /tekrarla - oynatılan parçayı istediğiniz kadar tekrar eder.
✦(örneğin: /tekrarla 4 - Parçayı 4 kez tekrarlar.)
➥ /restart - Admin Önbelleğini yeniler.
➥ /yetkiver - Grubunuzda yetkisiz üyeye yetki vererek botu kullandırabilirsiz.
➥ /yetkial - Grubunuzdaki botu kullanan yetkisiz üyeden bot yetkisini alır.
➥ /oynatmodu - Botun kullanım ayarlarını yapabilirsiniz.
➥ /ayarlar ve ya /settings - komutu kullanarak botun grup içi ayarlarını yapabilirsiniz.
/yetkilistesi [kullanıcıadı] - Grubunuzda bota yetki verdiğiniz kişiler."""


HELP_2 = """✅<u>**Oynat Komutları:**</u>✅

➥ /oynat - Şarkı oynatır.
✦ /oynat komutu aynı zamanda canlı yayında destekler.(örnek: /oynat kralfm canlı)
➥ /oynathemen - Sesli sohbette çalınan parçayı durdurur ve sırayı bozmadan temizlemeden aranan parçayı anında çalmaya başlar.
➥ /voynat - Video Oynatır.
✦ /voynat komutu aynı zamanda canlı yayınıda destekler.(örnek: /vplay kralfm canlı)
➥ /komutlar - Bu komutu Grubunuzda yazarak komutları görebilirsiniz.
✅Oynatma Listeleri:
/listem : komutla Listenize Eklediğiniz şarkılara Bakabilirsiniz..
/listemitemizle : Oynatma Listenizdeki Şarkıları Silebilirsiniz..
/oynat Komutunu Atarak Ekranda Çıkan Playlist tıklayıp direk Listenizi oynayabilirsiniz."""

HELP_3 = """✅<u>**Bot Komutları:**</u>✅

/stats : Bottaki Tüm İstatistikleri Görebilirsiniz. En Çok Müzik Oynatan Gruplar, Kullanıcılar, En Çok Oynatılan Müzikler Ve Daha Fazlası...
/sudolist : Bot sudo List.
/söz [Müzik Adı] : Sözlerine Bakmak İstediğiniz Şarkıyı Arayabilirsiniz.
/Bul [Müzik Adı] veya [Youtube Linki] : Youtubedan İndirmek İstediğiniz Şarkıyı İndirebilirsiniz.
/sira : Sırada Olan Müzikler Listesini Görebilirsiniz."""

HELP_4 = """✅<u>**Extra  Komutlar:**</u>✅

/start : Botun Başlatma Panelini Gösterir. 

/settings ve ya /ayarlar : Ayarlar Menüsüne Ulaşabilirsiniz.

/yardim : Botun Yardım Menüsüne Ulaşırsınız."""

HELP_5 = """✅<u>**Group Settings:**</u>
/settings - Bu Komutu Kullanarak Grup içi Bot Ayarlarını yapabilirsiniz.

🔗 **Ayarlardaki Seçenekler:**

1️⃣ Sesli sohbette yayınlamak istediğiniz **Ses Kalitesini** ayarlayabilirsiniz.

2️⃣ Sesli sohbette yayınlamak istediğiniz **Video Kalitesini** ayarlayabilirsiniz.

3️⃣ **Yetkilendirme Kullanıcıları**:- Yönetici komutları modunu buradan herkese veya yalnızca yöneticilere değiştirebilirsiniz. Grubunuzda bulunan herkes yönetici komutlarını kullanabilecekse (/atla,/durdur vb.)

4️⃣ **Temiz Mod:** Etkinleştirildiğinde, sohbetinizin temiz ve iyi kalmasını sağlamak için 5 dakika sonra botun mesajlarını grubunuzdan siler.

5️⃣ **Komut Temizleme** : Etkinleştirildiğinde, Bot yürütülen komutları (/oynat, /durdur, /karistir, /son vb.) hemen siler.

6️⃣ **Oynatma Komutları:**

/oynatmodu - Grubunuzun oynatma ayarlarını ayarlayabileceğiniz düğmeler içeren eksiksiz bir oynatma ayarları paneli gösterir. 

<u>Oynatma modundaki seçenekler:</u>

1️⃣ **Arama Modu** [Doğrudan veya Satır İçi] - /oynatmodu verirken arama modunuzu değiştirir.

2️⃣ **Yönetici Komutları** [Herkes veya Yöneticiler] - Grubunuzda bulunan herkes, herkes yönetici komutlarını kullanabilir (/atla, /durdur vb.)

3️⃣ **Oynat Türü** [Herkes veya Yöneticiler] - Yöneticilerse, yalnızca grupta bulunan yöneticiler sesli sohbette müzik çalabilir."""

HELP_5 = """🔰**<u>ADD & REMOVE SUDO USERS :</u>**
/addsudo [Username or Reply to a user]
/delsudo [Username or Reply to a user]
/gstats - komutunu kullanarak botun grup istatiklerini genel olarak görebilirsiniz.


🌐**<u>CONFIG VARS:</u>**
/get_var - Get a config var from Heroku or .env.
/del_var - Delete any var on Heroku or .env.
/set_var [Var Name] [Value] - Set a Var or Update a Var on heroku or .env. Seperate Var and its Value with a space.

🤖**<u>Bot Komutları:</u>**
/reboot - Botunuzu yeniden başlatın. 
/update - Botu Güncelle.
/speedtest - Sunucu hızlarını kontrol edin
/bakim [enable / disable] 
/logger [enable / disable] - Bot, logger grubunda aranan sorguları günlüğe kaydeder.
/get_log [Hat Sayısı] - Get log of your bot from heroku or vps. Works for both.
/autoend [enable|disable] - Hiç kimse dinlemiyorsa 3 dakika sonra otomatik akışı sonlandır özelliğini etkinleştirin.

📈**<u>İSTATİSTİK KOMUTLARI:</u>**
/aktifses - Botta aktif sesli sohbetleri kontrol edin.
/aktifvideo - Botta aktif görüntülü aramaları kontrol edin.
/stats - Bot İstatistiklerini Kontrol Edin.

⚠️**<u>KARA LİSTE SOHBET FONKSİYONU:</u>**
/grupban [CHAT_ID] - Music Bot kullanarak herhangi bir sohbeti kara listeye alın
/ungrupban [CHAT_ID] - Music Bot'u kullanarak kara listeye alınmış herhangi bir sohbeti beyaz listeye alın
/grupbanlist - Kara listeye alınmış tüm sohbetleri kontrol edin.

👤**<u>ENGELLENMİŞ KULLANICILAR:</u>**
/block [Kullanıcı adı veya bir kullanıcıya yanıt] - Bir kullanıcının bot komutlarını kullanmasını engeller.
/unblock [Kullanıcı adı veya bir kullanıcıya yanıt] - Bir kullanıcıyı Bot'un Engellenenler Listesinden çıkarın.
/blocklist - Engellenen Kullanıcı Listelerini Kontrol Edin

👤**<u>GBAN FONKSİYONU:</u>**
/gban [Kullanıcı adı veya bir kullanıcıya yanıt] - Botun sunduğu sohbetten bir kullanıcıyı Gban ve botunuzu kullanmasını engelleyin.
/ungban [Kullanıcı adı veya bir kullanıcıya yanıt] - Bir kullanıcıyı Bot'un gbanlı Listesinden çıkarın ve onun botunuzu kullanmasına izin verin
/gbannedusers - Gbanlı Kullanıcı Listelerini Kontrol Edin

🎥**<u>VİDEO ÇAĞRISI İŞLEVİ:</u>**
/videolimit [Sohbet Sayısı] - Bir seferde Görüntülü Aramalar için izin verilen maksimum Sohbet Sayısını ayarlayın. Varsayılan olarak 3 sohbet.
/videomodu [download|m3u8] - İndirme modu etkinleştirilirse Bot, videoları M3u8 biçiminde oynatmak yerine indirecektir. Varsayılan olarak M3u8'e. Herhangi bir sorgu m3u8 modunda oynatılmadığında indirme modunu kullanabilirsiniz.

⚡️**<u>ÖZEL BOT FONKSİYONU:</u>**
/authorize [CHAT_ID] - Botunuzu kullanmak için bir sohbete izin verin.
/unauthorize [CHAT_ID] - Bir sohbetin botunuzu kullanmasına izin vermeyin.
/authorized - Botunuzun izin verilen tüm sohbetlerini kontrol edin.

🌐**<u>REKLAM KOMUTLARI</u>**
/reklam [Mesaj veya Mesaja Cevap] - Herhangi bir mesajı Bot'un Sunulan Sohbetlerine yayınlayın.

<u>yayın seçenekleri:</u>
**-pin** : Bu, mesajınızı sabitleyecektir 
**-pinloud** : Bu, mesajınızı yüksek sesli bildirimle sabitleyecektir
**-user** : Bu, mesajınızı botunuzu başlatan kullanıcılara yayınlayacaktır.
**-assistant** : Bu, mesajınızı botunuzun asistan hesabından yayınlayacaktır.
**-nobot** : Bu, botunuzu mesaj yayınlamamaya zorlar

**Örnek:** `/reklam -user -assistant -pin MERHABA MİLLET`

"""
