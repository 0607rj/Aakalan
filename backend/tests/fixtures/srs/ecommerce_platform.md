# E-commerce Platform — Software Requirements Specification

Version 1.0 · Synthetic test document for Aakalan (not a real tender)

## 1. Overview and objectives

1.1 BeanBox sells its own coffee and brewing equipment and wants its own online store.
1.2 The objective is to take orders directly instead of through third-party marketplaces.
1.3 The warehouse team currently uses a barcode scanner app on its phones.

## 2. User roles and permissions

2.1 Roles: customer, store manager and administrator. Customers see only their own orders.

## 3. Functional requirements

3.1 The store shall show a product catalogue with photos, prices and variants.
3.2 Customers shall find products through advanced search with filters for price and roast.
3.3 Customers shall use a shopping cart and checkout as guests or with an account.
3.4 Customers shall pay through a payment gateway by card or UPI.
3.5 Customers shall subscribe to a monthly coffee box with recurring payments that they can pause or cancel.
3.6 Every order shall come with a GST invoice that the customer can download.
3.7 Customers shall track each order's status from packed to delivered.
3.8 The store manager shall see a dashboard of sales, orders and best sellers.

<!-- page -->

## 4. Non-functional requirements

4.1 The store shall be available 99.9% of the time.
4.2 The store shall be hosted on Microsoft Azure.

## 5. Security and data

5.1 Card details shall never be stored by the store; payments follow PCI DSS through the gateway.

## 6. Exclusions

6.1 Marketplace seller payouts are out of scope: BeanBox sells only its own products.
6.2 Video calls with customers are not required.

## 7. Future phase

7.1 A loyalty programme and a mobile app may be considered in phase 2.

## 8. Acceptance criteria

8.1 A guest can find a product, check out, pay and download the GST invoice.
8.2 A subscriber's card is charged each month until the subscription is cancelled.

## 9. Included and not included in this release

9.1 Included: catalogue, search, cart and checkout, payments, subscriptions, invoices, order tracking and the manager's dashboard.
9.2 Not included: seller payouts, video calls, loyalty programme and mobile app.
