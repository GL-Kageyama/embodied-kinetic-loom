// The two zero positions, read from this unit's own NVS.
//
// ⚠️ These are the only numbers in this firmware that were not read out of the
//    vendor's source. They are the vendor's setup wizard's measurement of this
//    unit — 460 and 620 when the unit was last observed booting — and they live
//    in the `servo` namespace that the vendor's firmware reads them from.
//
// ⛔ NVS is never erased here. If it cannot be read, the defaults are used and
//    the boot log says so. A zero is not a scale, and a default is not a zero.
#pragma once

namespace zeros {

// Returns true when both zeros came from NVS. On false, the vendor's defaults
// are written to the outputs and `from_nvs` says which happened.
bool read(int* yaw_zero, int* pitch_zero, bool* from_nvs);

}  // namespace zeros
