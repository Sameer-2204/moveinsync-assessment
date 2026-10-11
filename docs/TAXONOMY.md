# TAXONOMY v1.0

**Version:** 1.0  
**Date:** 2026-10-11  
**Status:** approved (GATE 3, 2026-10-11)  
**Derived from:** Open-coding of 160 stratified reviews (70 × 1-star, 30 × 2-3 star, 30 × 4-5 star from employee app; 20 × 1-2 star, 10 × 3-5 star from driver app)

---

## Themes

### 1. `app_crash_install`
**Definition:** App crashes, won't open, installation errors, "not installed from Play Store" errors, blank screens, forced reinstalls.

**Examples:**
- *"we use this app for our office commute, but it always crashes, giving an error that this app is not downloaded from app store, and then I have to uninstall and install it again"* (ID: 1518, rating 3)
- *"just keeps giving a blank screen everytime i try to open it"* (ID: 1251, rating 1)

---

### 2. `login_otp`
**Definition:** Cannot log in, OTP not received (phone or email), verification failures, authentication issues.

**Examples:**
- *"Unable to login in the App. Both Mobile Otp and Email OTP options are not working"* (ID: 1185, rating 1)
- *"what type of app is this... I'm not getting otp for log in whether it's Mail or phone."* (ID: 1890, rating 1)

---

### 3. `booking_scheduling`
**Definition:** Unable to book or schedule rides, booking failures, inability to edit bookings, calendar not working, adhoc booking issues, waitlist confusion.

**Examples:**
- *"waste app since unable to book cab from the app and also unable to see the calendar, very worst useless app"* (ID: 1402, rating 1)
- *"your new update is a threat to person with medical condition. it just books you without informing if he's on waitlist or not."* (ID: 19, rating 1)

---

### 4. `live_tracking_eta`
**Definition:** GPS/live tracking inaccurate, location frozen, ETA unreliable, map issues, cab location not updating in real-time.

**Examples:**
- *"most of the time driver location get stuck and keeps on showing at same place for like 30 mins"* (ID: 1794, rating 1)
- *"ETA calculator very bad. not sure on what basis its done. google maps always shows 3x the time shown in moveinsync app."* (ID: 15, rating 1)

---

### 5. `late_noshow_cab`
**Definition:** Cab arriving late, driver no-show, long wait times, cab not assigned on time. (Ops/vendor issue expressed through the app)

**Examples:**
- *"cab is never assigned on time...always late ..no value of others time...after logout every day we have to wait for 40+ mins"* (ID: 1858, rating 1)
- *"Taytay-Five Neo 615pm sched is always late! Always more than an hour late!"* (ID: 155, rating 1)

---

### 6. `routing_stops`
**Definition:** Bad route planning, inconvenient stops, long detours, pickup/drop locations in unsafe or inconvenient places, missing stop options.

**Examples:**
- *"They provide pickup and drop to the middle of nowhere from where its double work reaching our home or office"* (ID: 1314, rating 1)
- *"Just because my organization is using this service, we have to come to the office 1.5 hours before our shift starts, even though the ride itself takes only 10 minutes."* (ID: 1335, rating 1)

---

### 7. `driver_behavior_safety`
**Definition:** Rude or untrained drivers, safety concerns (especially for women at night), no-show marking without calling, driver speeding, unsafe boarding locations.

**Examples:**
- *"one of the worst services drivers don't know how to behave with employees and movein sync won't train them"* (ID: 1372, rating 1)
- *"No concern for female employees at logout time, they won't even call the employee at late night logout before making no show."* (ID: 1497, rating 1)

---

### 8. `ui_ux_design`
**Definition:** Poor UI design, confusing navigation, too many clicks, information not visible (pickup time, cab number, cab mate locations), forced notification permissions, annoying popups.

**Examples:**
- *"mobile number is not visible once cab is booked, I can not see latest notification... for every button click it is asking for policy acceptance"* (ID: 58, rating 1)
- *"The new feature and very annoying feature - when you click view otp, it pops up the seat belt safely first. Why do you ask for user input one more click"* (ID: 1, rating 2)

---

### 9. `notification_rating_prompt`
**Definition:** Excessive notifications, repeated rating prompts, spam-like cab delay pop-ups, forced ratings, no option to skip rating.

**Examples:**
- *"Please stop excessively notifying for Play Store reviews after every ride. It's wasting user time by repeated clicks."* (ID: 1550, rating 2)
- *"why the hell no option of skip rating. if I don't want rate."* (ID: 166, rating 1)

---

### 10. `app_performance`
**Definition:** App is slow, laggy, loading takes too long, high battery consumption, phone overheating, network errors despite good connectivity.

**Examples:**
- *"most of the time app keeps loading even in good internet connectivity."* (ID: 1842, rating 1)
- *"While traveling the app doesn't count accurate kilometres .some times app stuck... always my phone over heated and due to which all apps crash."* (ID: 263, rating 1, driver app)

---

### 11. `support_helpdesk`
**Definition:** Can't reach support/helpdesk, no escalation visibility, unresponsive support, no feedback channel, concerns not addressed.

**Examples:**
- *"no option to contact help desk"* (ID: 1226, rating 1)
- *"not avle to connect with helpdesk"* (ID: 198, rating 1)

---

### 12. `positive_general`
**Definition:** General positive feedback — easy to use, good app, great experience, safety features appreciated. (For 4-5 star reviews with positive sentiment)

**Examples:**
- *"employees can track their assigned cab and pick up and drop OTP....will enhance safely of employee"* (ID: 1299, rating 5)
- *"super good app and very ease to use"* (ID: 1695, rating 5)

---

### 13. `other_unclear`
**Definition:** Review too short, vague, in an unrecognizable language, or doesn't fit any other theme. Used when the classifier cannot confidently assign a theme.

**Examples:**
- *"bakwaas"* (ID: 1768, rating 1, Hindi slang for "rubbish")
- *"virbada"* (ID: 206, rating 1, unclear language)

---

## Attribution Guide

| Attribution | Definition | Example themes |
|------------|-----------|----------------|
| `app` | Issue is controllable by MoveInSync product/engineering | app_crash_install, login_otp, booking_scheduling, live_tracking_eta, ui_ux_design, notification_rating_prompt, app_performance |
| `ops_vendor` | Issue is about cab vendor operations, driver behavior, routing decisions | late_noshow_cab, routing_stops, driver_behavior_safety |
| `customer_policy` | Issue stems from the enterprise customer's transport policy (shift times, stop locations, booking windows) | routing_stops (sometimes), booking_scheduling (sometimes) |
| `unclear` | Cannot determine from the review text | other_unclear, very short reviews |

## Notes

- Many reviews blend themes (e.g., "app crashes AND cab is always late"). The classifier should return `themes[]` (all applicable) and `primary_theme` (the dominant one).
- Hinglish and regional-language reviews should be classified in their original language per A02.
- The `notification_rating_prompt` theme is particularly interesting — the app's own rating prompts may be driving negative Play Store reviews (a self-defeating cycle).
- `routing_stops` can be either `app` (if route optimization is MIS-controlled) or `customer_policy` (if the enterprise sets stop locations). Default to `unclear` when ambiguous.
