# MetLAN — Dongle kontrola berreraikitzeko kurtsoa

> Ibai-k proiektuaren zati bat (dongle-aren HiLink kontrola, `uhubctl` bidezko RF itzalketa, eta hori guztia FastAPI dashboard batera lotzea) berriz idatzi nahi du, zero-tik, ondo barneratzeko. Claude irakasle-rol batean dago: kodea ez du idazten, azalpenak eta ariketak ematen ditu, eta Ibai-k idatzitakoa berrikusten du.

**Lantokia:** `course` adarra, `metlan-dashboard-r-pi` repositorioan (Ibai-ren PC-an, `C:\prj\MetLAN-dashboard` eta `...OneDrive...\metlan-dashboard-r-pi`) + Raspberry Pi-an (`~/MetLAN-dashboard`, produkzioko zerbitzua gelditu eta karpeta bera berrerabiliz, jakinaren gainean).

**Metodologia:** modulu bakoitzak azalpen labur bat + ariketa bat ditu. Ibai-k kodea idazten du eta konpartitzen du; Claude-k ez du zuzenean konpontzen, zergatik ez duen funtzionatzen azaltzen du eta pista bat ematen du (ez soluzio osoa, berariaz eskatu ezean).

---

## 0. Aurretiko urratsak (eginda)

- [x] `course` adar hutsa sortu repositorioan (PC-an).
- [x] Raspberry Pi-an dependentziak instalatu (`fastapi==0.115.0`, `uvicorn[standard]==0.30.6`, `psutil==6.0.0`, `huawei-lte-api==2.0.1`), Pi-a garbitu ondoren (sare-konfigurazioa, `dnsmasq`, `nftables`, `metlan-gui.service` guztiak kenduta, oinarrizko OS/SSH/erabiltzailea mantenduz).
- [x] Sarea berriz testbench isolatura itzuli, dongle-a konektatuta.

---

## 1. Modulua — HiLink APIaren oinarriak

**Zer ikasi behar den:** dongle-ak (Huawei E3372h-607) bere web-zerbitzari txiki bat du barruan (`http://192.168.8.1`), eta `huawei-lte-api` liburutegiak horrekin hitz egiten du HTTP bidez. `Connection` klaseak sesioa irekitzen du; `Client`-ek API-taldeak eskaintzen ditu (`monitoring`, `dial_up`, `pin`...).

**Ariketa 1.1:** idatzi script bat (`modem_service.py` edo antzeko izena) dongle-arekin konektatu eta `monitoring.status()`-en emaitza inprimatzen duena. Bereziki begiratu `ConnectionStatus` eremua.

**Ariketa 1.2:** identifikatu `ConnectionStatus`-en balio posibleak (`900`-`904`) eta zer esan nahi duten (`connecting`, `connected`, `disconnected`, `disconnecting`, `connect failed`).

*(Hemen gaude orain — Ibai-k 1.1 ariketa hasi du.)*

---

## 2. Modulua — Konexioa piztu/itzali, eta zergatik den bereziki bihurria dongle honetan

**Zer ikasi behar den:**
- `dial_up.set_mobile_dataswitch(dataswitch=1)` erregistratzen du sarean, baina **ez du markatzen** — dongle honek `ConnectMode` eskuzkoa du, beraz `dial()` ere deitu behar da.
- `dial_up.dial()`-ek `Action: 1` bidaltzen du `dialup/dial` amaierara.
- **Ez dago `hangup()` publikorik liburutegian** — itzaltzeko, `Action: 0` bidali behar da eskuz, `_session.post_set(...)` bidez (API pribatua, `client.dial_up._session`).
- **`dataswitch` ez da fidagarria egoera irakurtzeko** dongle honetan — `'0'` irakur dezake konektatuta egon arren. Egoera benetan jakiteko, `monitoring.status()`-en `ConnectionStatus` erabili, ez `dataswitch`.

**Ariketa 2.1:** gehitu `enable()`/`disable()` funtzioak — `enable`-k `dataswitch=1` + `dial()` egin behar ditu; `disable`-k `Action: 0` bidali behar du zuzenean.

**Ariketa 2.2:** frogatu benetan zer gertatzen den dongle-aren LED-arekin `disable()` egitean — geratzen al da erregistratuta sarean (LED cyan keinuka) data-saioa amaitu arren? (Hau da hurrengo moduluaren giltza.)

---

## 3. Modulua — SIM PIN kudeaketa

**Zer ikasi behar den:** SIM blokeatuta badago, dongle-ak "ez detektatuta" bezala erakusten du, ez "PIN behar du" bezala. `client.pin.operate(operate_type="0", current_pin=PIN)` deitu behar da konexio-egiaztapen bakoitzaren aurretik, best-effort moduan (PIN behar ez bada edo dagoeneko desblokeatuta badago, errorea itzuliko du — hori ez da arazo bat).

**Ariketa 3.1:** gehitu PIN desblokeatze-funtzio bat, konfiguragarria (aldagai bat edo `.env` fitxategi batetik), eta deitu `get_status()`/`enable()`/`disable()` bakoitzaren hasieran.

---

## 4. Modulua — Guztia FastAPI router batera lotu

**Zer ikasi behar den:** FastAPI-ren oinarriak — `APIRouter`, `prefix`, `@router.get`/`@router.post`, eta nola muntatzen den `app.include_router()` bidez `main.py`-n.

**Ariketa 4.1:** sortu `app/routers/modem.py`, `/api/modem` prefixarekin, eta hiru endpoint: `GET /status`, `POST /power?enable=bool`, `GET /log` (ekintza-erregistro sinple bat, memorian).

**Ariketa 4.2:** sortu `app/main.py` minimo bat, router hori muntatzen duena, eta probatu `uvicorn app.main:app --reload`-ekin + `curl`.

---

## 5. Modulua — Benetako RF itzalketa (`uhubctl`)

**Zer ikasi behar den:** aurreko moduluetako `disable()`-k ez du benetan itzaltzen erradioa (dongle-a erregistratuta gelditzen da sarean). Raspberry Pi 4-ak berak USB atalen potentzia benetan mozteko gaitasuna du (`uhubctl`), baina bi hub-zuhaitz batera aldatu behar dira (`-l 2` eta `-l 1-1`), atal guztiak elkarrekin lotuta baitaude Pi 4-an.

**Ariketa 5.1:** `subprocess` bidez, idatzi `usb_power_service.py`, `uhubctl -l 2 -a 0/1` eta `-l 1-1 -a 0/1` deitzen dituena, eta huts egiten badu (binarioa falta, `sudo` baimenik ez) modu "leunean" huts egiten duena (`available: false`, ez krash).

**Ariketa 5.2:** frogatu benetan itzaltzen dela LED-a `uhubctl -a 0` egitean, eta berreskuratzen dela automatikoki `-a 1`-ekin (`eth1` interfazea berriz agertuz DHCP berri batekin).

---

## 6. Modulua — Bi zerbitzuak uztartu: ON/OFF sinplea

**Zer ikasi behar den:** erabiltzaile arruntarentzat, bi kontrol-geruzak (data-saioa + RF potentzia) botoi bakar batean bildu behar dira. **OFF**-ek beti egin behar du benetako USB potentzia-mozketa. **ON**-ek USB piztu, HiLink APIa berriz erantzuten hasi arte itxaron (poll-a), eta orduan markatu — eta **saiakera bat baino gehiago** egin behar da markatzeko, lehenengoa askotan huts egiten baitu dongle-a oraindik erregistratzen ari den bitartean.

**Ariketa 6.1:** idatzi `dongle_control.py`, `power_on()`/`power_off()`/`get_status()` funtzioekin, aurreko bi zerbitzuak (`modem_service`, `usb_power_service`) uztartzen dituena.

**Ariketa 6.2 (erronka):** gehitu dial-aren erreintentu-logika — zergatik behar den, eta nola frogatu benetan konektatu dela behin baino gehiagotan saiatu ondoren.

---

## 7. Modulua — Frontend minimoa

**Zer ikasi behar den:** HTML/JS soila (framework-rik gabe), `fetch()` bidez API-ari deitzeko, eta `setInterval` bidez egoera periodikoki eguneratzeko.

**Ariketa 7.1:** sortu ON/OFF botoi bakarreko orri bat, egoera erakusten duena eta botoiak `dongle_control`-en endpoint-etara deitzen dutenak.

**Ariketa 7.2 (aukerakoa):** gehitu "Advanced" atal tolesgarri bat, geruza banatuen kontrolekin (data-saioa bakarrik / USB potentzia bakarrik), depuratzeko.

---

## 8. Modulua (aukerakoa) — Router konfigurazioa: `nftables` + `dnsmasq`

Hau egin da jada proiektuko benetako kodean, eta konplexuagoa da (sarea/NAT/DHCP). Ibai-k erabaki dezake hemen sartu nahi duen, ala kode hori dagoeneko ondo ulertuta duen eta aurreko moduluetan zentratu nahi duen.

---

## Erabilitako baliabideak

- `huawei-lte-api` liburutegiaren iturburu-kodea (`Client.py`, `Connection.py`, `api/DialUp.py`, `api/Monitoring.py`, `api/Pin.py`) — lagungarria da API-ren metodo publikoak zein diren ikusteko.
- FastAPI-ren dokumentazio ofiziala: https://fastapi.tiangolo.com/
- `uhubctl`: https://github.com/mvp/uhubctl

---

*Dokumentu hau bizirik dago — modulu bat bukatzen den bakoitzean, markatu `[x]` eta gehitu oharrak beharrezkoa bada.*