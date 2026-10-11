# MoveInSync Play Store Ratings: Evidence-Linked Recommendations

Generated: 2026-10-11  
Status: final project package with a documented rule-based classification fallback. See limitations before using priorities for investment decisions.

## Decision-ready recommendation

The collected MoveInSync employee-app text-review dataset contains **1003 reviews** from **2016-10-04 to 2026-10-09**. Its mean rating is **3.77/5**; **293 (29.2%, 95% CI 26.5%–32.1%)** are 1–2-star reviews. These are collected text reviews, not the complete Play Store rating population.

Prioritize the recommendations below by the modeled rating-points-lost estimate: the difference between the observed mean review rating and the mean if the focal theme's reviews instead matched all other collected reviews. It is a diagnostic counterfactual, not a forecast.

## Prioritized actions
### 1. `booking_scheduling`

**Evidence.** n=49 (4.9% of collected employee reviews); 35 1–2-star reviews (11.9% of collected 1–2-star reviews); mean rating 2.20; modeled rating points lost 0.081.

**Proof from verbatim reviews.**
> “The recent updates in the UI have made the app very difficult to use. Booking a shuttle is now a 2 step process previously it used to be 1. I got confused and thought I had booked a cab while I hadn't. Was too late in realising that. Such major changes need to be released in a better way rather than just throwing them in the user's face. Another bad thing is even though I am in 1 cab but I can see all the ones available for that time. I don't need to see others, just show me mine.” — review ID 1699 (1★)
> “There should be an option to directly search for seat number instead of using the map. There should be an option to set default floor in app and portal. Multiple times for multiple people, the seat number (booking shows but without desk allocation) gets removed for bookings which is a major bug” — review ID 1254 (1★)
> “does not let you book a bus if location accuracy is off. why do you need location accuracy? are you going to bring the bus to my house? well it does not even let you scan QR code now without location accuracy. thanks guys. any more ways you can make your app more useless?” — review ID 1625 (1★)

**Fix.** Make booking state, cut-off, waitlist, and edit eligibility explicit on one screen; provide actionable errors and route roster conflicts to the transport desk.

**Owner / effort.** Product + Engineering; M (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** Booking completion rate, booking-error rate, and 1–2-star booking reviews.

### 2. `live_tracking_eta`

**Evidence.** n=43 (4.3% of collected employee reviews); 26 1–2-star reviews (8.9% of collected 1–2-star reviews); mean rating 2.49; modeled rating points lost 0.057.

**Proof from verbatim reviews.**
> “The GPS tracking system is very slow, and the pickup and drop timings are frequently incorrect. Additionally, the live location of other users is often not visible. Due to these issues, we are unable to determine the correct vehicle location, which is causing inconvenience. Kindly investigate and resolve these issues as soon as possible.” — review ID 1766 (1★)
> “-still as horrible as it can be. I had the details loaded on my wifi. I stepped in a no network zone and it logged me out! what security you need that you would log out a user if no network for just some seconds. absolutely sick idiots wasting mornings since years. -stupid app, worse routing algo. picked me up first, then second, and came back to my society after 30 mins for third pickup. -clicking on View ETA opens maps, but adds KING confident speaking before my home address, maybe hacked” — review ID 1900 (1★)
> “when we have zoomed in the map to track a vehicle what's the necessity to zoom out and show the ETA” — review ID 1482 (2★)

**Fix.** Show last GPS update time and confidence, suppress stale ETAs, and provide a clear fallback status when vehicle telemetry is unavailable.

**Owner / effort.** Engineering; M (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** Fresh-location rate, ETA error, and 1–2-star tracking/ETA reviews.

### 3. `login_otp`

**Evidence.** n=27 (2.7% of collected employee reviews); 21 1–2-star reviews (7.2% of collected 1–2-star reviews); mean rating 1.81; modeled rating points lost 0.054.

**Proof from verbatim reviews.**
> “The new feature and very annoying feature which you have introduced - when you click view otp , it pops up the seat belt safely first. Why do you ask for user input one more click . very annoying I should be able to see the otp in one click.” — review ID 1 (2★)
> “Such a worst app. I am not receiving the OTP even after trying multiple times. Because of this, I am unable to complete the login/verification process. Please fix this issue as soon as possible.” — review ID 115 (1★)
> “I try to login to this app but it's not sending any otp to login without login how we can use this app 😤😤😤 technical team please check once about this issue” — review ID 62 (1★)

**Fix.** Add OTP delivery-status feedback, resend fallback, and a self-serve recovery path; log provider and channel failures by tenant without exposing personal data.

**Owner / effort.** Engineering; M (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** OTP completion rate, login success rate, and 1–2-star login/OTP reviews.

### 4. `app_crash_install`

**Evidence.** n=23 (2.3% of collected employee reviews); 17 1–2-star reviews (5.8% of collected 1–2-star reviews); mean rating 1.70; modeled rating points lost 0.049.

**Proof from verbatim reviews.**
> “Move in sync app after every couple of days when I try to use it it shows unable to open as the app was not downloaded from play store which is a fake msg. Hence ever time this happens I have to uninstall it and then reinstall. Need a permanent fix to this problem.” — review ID 160 (1★)
> “first if the all the app itself is garbage , would crash after every 20days. Then the service , I dont know why companies even go with these retarded service , no ethics and no responsibility at all. Companies should absolutely avoid” — review ID 178 (1★)
> “whenever i update this app, i am not able to open the app again, I need to uninstall and reinstall again. facing this issue since 3 months” — review ID 4 (1★)

**Fix.** Instrument launch/install failures by app version and device; show a recoverable in-app error with support diagnostics rather than forcing reinstall.

**Owner / effort.** Engineering; M (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** Crash-free sessions and 1–2-star crash/install reviews.

### 5. `late_noshow_cab`

**Evidence.** n=18 (1.8% of collected employee reviews); 13 1–2-star reviews (4.4% of collected 1–2-star reviews); mean rating 2.00; modeled rating points lost 0.032.

**Proof from verbatim reviews.**
> “I had a suggestion to add a smart notification feature to remind the user for check-in after the vehicle crosses their pickup point. Sometimes, the vehicle arrives late or we miss by mistake to check-in, then we are marked as "No show" and it comes as a surprise. Introducing this one feature will help a lot for both transportation and end users. This may sound silly but even a small thing matters a lot.” — review ID 1795 (1★)
> “works well overall, but they don't listen to feedback. for example, pick ups from same apartment complex are scheduled with difference of upto 5 minutes. So, I come to the cab everyday, and wait 5 minutes for next passanger, and then another 5 minutes for the third passanger coming from same building. the third passanger can come upto 5 minutes late. so, I have waiting time of 10-15 minutes everyday just sitting in the cab. They don't care enough to fix it even after raising it 100s of times.” — review ID 1316 (1★)
> “cab is never assigned on time...always late ..no value of others time...after logout every day we have to wait for 40+ mins for cab the 20 mins distance route...which is totally waste of time...third class” — review ID 1858 (1★)

**Fix.** Create an operations alert when assignment or pickup exceeds its SLA; send proactive delay explanation and an escalation link, and review vendor performance weekly.

**Owner / effort.** Ops; M (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** On-time pickup rate, no-show rate, and 1–2-star late/no-show reviews.

### 6. `routing_stops`

**Evidence.** n=23 (2.3% of collected employee reviews); 13 1–2-star reviews (4.4% of collected 1–2-star reviews); mean rating 2.57; modeled rating points lost 0.028.

**Proof from verbatim reviews.**
> “utter disaster, this app algorithm is worse, it took me 2.5 hr to reach my home to which I usually reach in 50 minutes if I take a long route. they have paired with people who belong to different areas. no one responded even after raising my concern.” — review ID 1597 (1★)
> “worst routine system... all idiots engineers low profile people are making tool and giving routing system worst. my house is 40min from office it take 2.5 hours for me to reach home.” — review ID 1279 (1★)
> “They do clubbing very badly, even club people in a single cab where people are not from the same route.” — review ID 1424 (1★)

**Fix.** Expose the policy-controlled pickup/drop rationale, capture exception requests, and give customer transport desks a weekly list of high-friction stops and detours.

**Owner / effort.** Customer Success + Ops; L (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).

**Success measure.** Route-duration variance, approved exception rate, and 1–2-star routing/stop reviews.

## Ownership split

The labels explicitly separate product-controllable, operations/vendor, customer-policy and unclear issues. Route ops/vendor themes to vendor management and the relevant enterprise transport desk; do not treat them as app defects solely because the review is posted on the app page.

## Methods and limitations

- Source: public Google Play reviews collected with `google-play-scraper`; raw payloads are retained in Postgres. The collected sample is 1003 employee-app reviews, not every Play Store rating or review.
- Taxonomy: approved v1.0, derived from a 160-review stratified open-coding sample.
- Classification: 2326 reviews were assigned using a transparent regex fallback under `rule-v1` because the configured Gemini free-tier quota was exhausted. The fallback labels are not an LLM evaluation, and independent classifier accuracy/Cohen's kappa are UNKNOWN.
- Selection bias: reviews with text are not representative of ratings without text. Conclusions are about the collected review sample.
- All numbers and quotes in this document are rendered by `scripts/build_final_recommendation.py`; quoted review IDs identify the underlying stored reviews.
