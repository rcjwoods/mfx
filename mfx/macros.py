from ophyd.status import wait as status_wait
from mfx.db import (mfx_reflaser,
                    mfx_tfs,
                    mfx_dg1_ipm,
                    mfx_dg2_ipm,
                    mfx_dg1_slits,
                    mfx_dg1_wave8_motor,
                    mfx_dg2_upstream_slits,
                    mfx_dg2_midstream_slits,
                    mfx_dg2_downstream_slits)
import numpy as np
import time


def laser_in(wait=False, timeout=10):
    """
    Insert the Reference Laser and clear the beampath

    Parameters
    ----------
    wait: bool, optional
        Wait and check that motion is properly completed

    timeout: float, optional
        Time to wait for motion completion if requested to do so

    Operations
    ----------
    * Insert the Reference Laser
    * Set the Wave8 out (35 mm)
    * Set the DG1 slits to 6 mm x 6 mm
    * Set the DG2 upstream slits to 6 mm x 6 mm
    * Set the DG2 midstream slits to 1 mm x 1 mm
    * Set the DG2 downstream slits to 1 mm x 1 mm
    """
    # Command motion and collect status objects
    ref = mfx_reflaser.insert(wait=False)
    tfs = mfx_tfs.remove_all()
    dg1_ipm=mfx_dg1_ipm.target.remove()
    dg2_ipm=mfx_dg2_ipm.target.remove()
    dg1 = mfx_dg1_slits.move(6., wait=False)
    dg2_us = mfx_dg2_upstream_slits.move(6., wait=False)
    dg2_ms = mfx_dg2_midstream_slits.move(1., wait=False)
#    dg2_ds = mfx_dg2_downstream_slits.move(1., wait=False)
    # Combine status and wait for completion
    if wait:
        status_wait(ref & dg1 & dg2_us & dg2_ms,
                    timeout=timeout)


def laser_out(wait=False, timeout=10):
    """
    Remove the Reference Laser and configure the beamline

    Parameters
    ----------
    wait: bool, optional
        Wait and check that motion is properly completed

    timeout: float, optional
        Time to wait for motion completion if requested to do so

    Operations
    ----------
    * Remove the Reference Laser
    * Set the Wave8 Target 3 In (5.5 mm)
    * Set the DG1 slits to 0.7 mm x 0.7 mm
    * Set the DG2 upstream slits to 0.7 mm x 0.7 mm
    * Set the DG2 midstream slits to 0.7 mm x 0.7 mm
    * Set the DG2 downstream slits to 0.7 mm x 0.7 mm
    """
    # Command motion and collect status objects
    ref = mfx_reflaser.remove(wait=False)
# Removing dg1 wave8 movement for now, until wave8 target positions have been fixed
#    w8 = mfx_dg1_wave8_motor.move(5.5, wait=False)
    dg1 = mfx_dg1_slits.move(0.7, wait=False)
    dg2_us = mfx_dg2_upstream_slits.move(0.7, wait=False)
    dg2_ms = mfx_dg2_midstream_slits.move(0.7, wait=False)
#    dg2_ds = mfx_dg2_downstream_slits.move(0.7, wait=False)
    # Combine status and wait for completion
    if wait:
        status_wait(ref & w8 & dg1 & dg2_us & dg2_ms ,
                    timeout=timeout)


def mfxslits(pos):
    """Set all the slits to specific position"""
    dg1 = mfx_dg1_slits.move(pos, wait=False)
    dg2_us = mfx_dg2_upstream_slits.move(pos, wait=False)
    dg2_ms = mfx_dg2_midstream_slits.move(pos, wait=False)
    dg2_ds = mfx_dg2_downstream_slits.move(pos, wait=False)


class FakeDetector:
    def __init__(self, detname='Rayonix'):
        try:
            self.detname = detname
            if detname == 'Rayonix':
                # below is 4x4 binning (https://www.rayonix.com/product/mx340-hs/)
                self.pixel_size_mm = 0.177
                self.pixel_per_side = 1920
                self.beam_stop_radius_mm = 5
            elif detname == 'epix10k2M':
                # see https://lcls.slac.stanford.edu/detectors/ePix10k
                self.pixel_size_mm = 0.100
                self.pixel_per_side = 1650 # approximate
                self.beam_stop_radius_mm = 9 # approximate
        except:
            print('Detector not implemented.')


    def _energy_keV_to_wavelength_A(self, energy_keV):
        return 12.398 / energy_keV


    def _pixel_index_to_radius_mm(self, pixel_index):
        return pixel_index * self.pixel_size_mm


    def _pixel_radius_mm_to_theta_radian(self, pixel_radius_mm, det_dist_mm):
        # angle between incident and outgoing wavevectors: 2*theta
        return np.arctan2(pixel_radius_mm, det_dist_mm) / 2.0


    def _pixel_theta_radian_to_q_invA(self, pixel_theta_radian, wavelength_A):
        # q = 2pi.s = 4pi.sin(theta)/lambda
        return 4 * np.pi * np.sin(pixel_theta_radian) / wavelength_A


    def _pixel_q_invA_to_resol_A(self, pixel_q_invA):
        # d = 1/s = 2pi/q
        return 2 * np.pi / pixel_q_invA


    def _pixel_radius_mm_to_q_invA(self, radius_mm, det_dist_mm, energy_keV):
        return \
            self._pixel_theta_radian_to_q_invA(
                self._pixel_radius_mm_to_theta_radian(radius_mm, det_dist_mm),
                self._energy_keV_to_wavelength_A(energy_keV)
        )


    def resolution_coverage(self, energy_keV=None, det_dist_mm=None):
        low_q_invA = self._pixel_radius_mm_to_q_invA(
            self.beam_stop_radius_mm, det_dist_mm, energy_keV
        )
        high_q_invA = self._pixel_theta_radian_to_q_invA(
            self._pixel_radius_mm_to_theta_radian(
                self._pixel_index_to_radius_mm(self.pixel_per_side/2.0), det_dist_mm
            ), self._energy_keV_to_wavelength_A(energy_keV)
        )
        highest_q_invA = self._pixel_theta_radian_to_q_invA(
            self._pixel_radius_mm_to_theta_radian(
                self._pixel_index_to_radius_mm(self.pixel_per_side / np.sqrt(2.0)), det_dist_mm
            ), self._energy_keV_to_wavelength_A(energy_keV)
	)

        print(f"### FakeDetector {self.detname} resolution range:")
        print(f"### - Energy: {energy_keV} keV")
        print(f"### - Distance: {det_dist_mm} mm")
        print(f">>> Low q    : {low_q_invA:.2f} A-1 | {self._pixel_q_invA_to_resol_A(low_q_invA):.2f} A")
        print(f">>> High q   : {high_q_invA:.2f} A-1 | {self._pixel_q_invA_to_resol_A(high_q_invA):.2f} A (detector edge)")
        print(f">>> Highest q: {highest_q_invA:.2f} A-1 | {self._pixel_q_invA_to_resol_A(highest_q_invA):.2f} A (detector corner)")


def get_exp():
    import requests
    ws_url = "https://pswww.slac.stanford.edu/ws/lgbk"
    resp = requests.get(
        ws_url + "/lgbk/ws/activeexperiment_for_instrument_station",
        {"instrument_name": 'mfx', "station": 0})
    exp = resp.json().get("value", {}).get("name")
    return exp
