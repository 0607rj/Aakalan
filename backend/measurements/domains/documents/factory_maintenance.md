# Plant Maintenance System — Requirement Document

Version 1.0 · Synthetic measurement document for Aakalan (not a real tender)

## 1. Background

1.1 Shakti Auto Components runs two plants in Pune with 320 machines: presses, CNC machines, robots and compressors.
1.2 Breakdowns are reported on paper slips and maintenance history is in Excel. The plants want a maintenance system for the maintenance team and the stores.
1.3 SAP is used for purchasing and accounts and stays the system of record for purchase orders.

## 2. Users

2.1 Machine operators, maintenance technicians, maintenance supervisors, the stores team and the plant head will use the system.

<!-- page -->

## 3. Functional requirements

3.1 Every machine shall have a record with its make, model, location, manuals and maintenance history.
3.2 Operators shall raise a breakdown request by scanning the QR code on the machine with a phone.
3.3 Supervisors shall create work orders, assign technicians and set priorities; technicians shall close work orders with the work done, time spent and spares used.
3.4 The system shall create preventive maintenance work orders on schedule, by calendar or by running hours.
3.5 Technicians shall use an Android app to see and update their work orders, take photos and follow checklists.
3.6 The technician app shall work inside the plant where Wi-Fi is weak and send updates when back in range.
3.7 The stores team shall keep stock of spare parts with bin locations and minimum levels, and issue spares against work orders.
3.8 Spare part purchase requests above ₹25,000 shall go to the plant head for approval, and approved requests shall be sent to SAP.
3.9 Sensors on the compressors and presses send temperature and vibration readings every minute; the system shall store these readings and alert supervisors when a reading crosses its limit.
3.10 The system shall predict likely failures of the compressors from the sensor readings and past breakdowns.
3.11 Supervisors shall get an app notification and SMS for every breakdown on a critical machine.
3.12 The plant head shall see dashboards of downtime, mean time between failures, mean time to repair and maintenance cost per machine.
3.13 Maintenance history of the last two years shall be moved from the existing Excel sheets.

<!-- page -->

## 4. Exclusions

4.1 Production planning and quality inspection are out of scope.
4.2 An iPhone app is not required.

## 5. Support

5.1 The vendor shall support the system for two years with round-the-clock on-call support.
