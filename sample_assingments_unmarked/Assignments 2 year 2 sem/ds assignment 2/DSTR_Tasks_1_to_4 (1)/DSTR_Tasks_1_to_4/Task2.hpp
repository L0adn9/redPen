#ifndef TASK2_H
#define TASK2_H

#include "Common.hpp"

void runTask2Menu();
void createServiceRequest(Parcel* parcel, RouteAction route);

// Save every service request to task2_requests.txt (also called automatically
// after every change; requests are loaded automatically when first needed).
void saveServiceRequests();

// Used by Task 3: Request ID of the ACTIVE (pending / processing) request of a
// parcel, or "" if the parcel has none. Exposes one value, not the request list.
string getActiveRequestID(const string& parcelID);

// Close open requests whose parcel was finished elsewhere (Task 1 set it to
// Collected / Returned / Cancelled, or reported it Missing) and free the
// parcel's Task 3 resource. Returns true if anything changed.
bool syncRequestsWithParcels();

#endif
