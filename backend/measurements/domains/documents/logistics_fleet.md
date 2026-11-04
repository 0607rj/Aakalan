# Fleet and Delivery Management Platform — Requirement Document

Version 1.0 · Synthetic measurement document for Aakalan (not a real tender)

## 1. Background

1.1 RoadLink Cargo runs 140 trucks and delivers goods for about 300 business customers across Maharashtra and Gujarat.
1.2 Dispatchers today plan trips on phone calls and WhatsApp. RoadLink wants a platform for its office team, its drivers and its customers.
1.3 Accounts are kept in Tally, which shall stay the accounting system.

## 2. Users

2.1 Dispatchers, drivers, fleet managers, accounts staff and business customers will use the platform.

<!-- page -->

## 3. Functional requirements

3.1 Dispatchers shall create delivery trips, assign a truck and a driver, and add the stops in order.
3.2 The system shall suggest the best order of stops for a trip to reduce distance and time.
3.3 Every truck carries a GPS tracker; the platform shall read the trackers' locations every minute from the tracker company's API.
3.4 Dispatchers and customers shall see trucks live on a map, with the expected arrival time at each stop.
3.5 Drivers shall use an Android app to see their trips, start and finish each stop, and call the customer.
3.6 Drivers shall scan the barcode on every parcel at pickup and delivery with the phone camera.
3.7 At delivery the driver shall capture the receiver's signature and a photo as proof of delivery.
3.8 The driver app shall keep working on highways without mobile network and send the data when the network returns.
3.9 Customers shall receive an SMS with a tracking link when their parcel is out for delivery.
3.10 Drivers shall enter fuel fills and repair costs; fleet managers shall see each truck's fuel use and service due dates.
3.11 Trip expenses above ₹5,000 shall go to the fleet manager for approval.
3.12 Accounts staff shall generate GST freight invoices for customers each month.
3.13 Invoices and payments shall be sent to Tally automatically every day.
3.14 Fleet managers shall see reports of trips, delays, fuel cost per kilometre and on-time delivery.

<!-- page -->

## 4. Exclusions

4.1 Customers pay by bank transfer; online payment on the platform is not required.
4.2 An iPhone version of the driver app is not required.

## 5. Support

5.1 The vendor shall support the platform for three years, including round-the-clock on-call support for the driver app.
