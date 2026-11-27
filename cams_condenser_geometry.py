
from dataclasses import dataclass
import math


@dataclass
class CondenserGeometry:
    """
    CAMS Condenser Geometry Model V1.2

    Offset Strip Fin Geometry

    Coordinate convention:
        X: Core width, 500 mm
        Y: Core height, 200 mm
        Z: Airflow direction, 65 mm

    Fin arrangement:
        Pitch along X direction.
        Fin segment length along Z direction.
        Adjacent segments use staggered offset arrangement.

    Note:
        This is a geometric accounting model.
        Offset-fin j/f correlations are not included.
    """

    # =====================================================
    # 1. Core dimensions
    # =====================================================

    W_core: float = 0.500
    H_core: float = 0.200
    L_air: float = 0.065
    L_oil: float = 0.500

    # =====================================================
    # 2. Flat tube geometry
    # =====================================================

    N_tube: int = 20

    H_tube: float = 0.0025

    t_wall: float = 0.0003
    t_side: float = 0.0003
    t_web: float = 0.0003

    N_port: int = 14
    N_pass: int = 4

    # =====================================================
    # 3. Offset strip fin geometry
    # =====================================================

    H_fin: float = 0.0075

    # Fin pitch along core width
    s_fin: float = 0.0020

    # Fin material thickness
    t_fin: float = 0.0001

    # Total fin depth
    l_fin: float = 0.065

    # Individual offset strip length
    l_offset: float = 0.006

    # Adjacent strip offset ratio
    # Provisional: half segment length
    offset_ratio: float = 0.5

    # =====================================================
    # 4. Edge margins
    # =====================================================

    H_edge: float = 0.00375

    # =====================================================
    # 5. Material properties
    # =====================================================

    rho_al: float = 2700.0

    # =====================================================
    # 6. Geometry calculation
    # =====================================================

    def calculate(self):

        # -------------------------------------------------
        # A. Input validation
        # -------------------------------------------------

        assert self.W_core > 0
        assert self.H_core > 0
        assert self.L_air > 0
        assert self.L_oil > 0

        assert self.N_tube > 1
        assert self.N_port > 0
        assert self.N_pass > 0

        assert self.N_tube % self.N_pass == 0

        assert self.H_tube > 2 * self.t_wall
        assert self.s_fin > self.t_fin
        assert self.l_offset > 0
        assert self.l_fin > 0

        # -------------------------------------------------
        # B. Flat tube internal geometry
        # -------------------------------------------------

        h_port = (
            self.H_tube - 2 * self.t_wall
        )

        w_internal = (
            self.L_air
            - 2 * self.t_side
            - (self.N_port - 1) * self.t_web
        )

        assert w_internal > 0

        w_port = (
            w_internal / self.N_port
        )

        A_port = (
            w_port * h_port
        )

        A_tube = (
            self.N_port * A_port
        )

        Dh_oil = (
            4 * A_port
            / (2 * (w_port + h_port))
        )

        # Total oil-side flow area
        A_oil_total = (
            self.N_tube * A_tube
        )

        # -------------------------------------------------
        # C. Flow pass geometry
        # -------------------------------------------------

        tubes_per_pass = (
            self.N_tube // self.N_pass
        )

        N_port_total = (
            self.N_tube * self.N_port
        )

        N_port_per_pass = (
            tubes_per_pass * self.N_port
        )

        A_pass = (
            tubes_per_pass * A_tube
        )

        # -------------------------------------------------
        # D. Core stacking geometry
        # -------------------------------------------------

        N_gap = self.N_tube - 1

        H_stack = (
            2 * self.H_edge
            + self.N_tube * self.H_tube
            + N_gap * self.H_fin
        )

        height_error = (
            H_stack - self.H_core
        )

        # -------------------------------------------------
        # E. Fin pitch geometry
        # -------------------------------------------------

        s_clear = (
            self.s_fin - self.t_fin
        )

        N_fin = int(
            round(self.W_core / self.s_fin)
        )

        actual_fin_width = (
            N_fin * self.s_fin
        )

        width_error = (
            actual_fin_width - self.W_core
        )

        fin_open_ratio = (
            s_clear / self.s_fin
        )

        # -------------------------------------------------
        # F. Offset strip segmentation
        # -------------------------------------------------

        # Number of complete segments
        N_offset_full = int(
            self.l_fin // self.l_offset
        )

        # Remaining partial segment
        l_partial = (
            self.l_fin
            - N_offset_full * self.l_offset
        )

        tolerance = 1e-12

        if l_partial < tolerance:
            l_partial = 0.0
            N_offset_partial = 0
        else:
            N_offset_partial = 1

        # Total segments per fin track
        N_offset_per_track = (
            N_offset_full + N_offset_partial
        )

        # Total segment count
        N_offset_total = (
            N_fin * N_gap * N_offset_per_track
        )

        # Provisional stagger displacement
        l_offset_shift = (
            self.l_offset * self.offset_ratio
        )

        # -------------------------------------------------
        # G. Fin material volume
        # -------------------------------------------------

        # Exact total fin material volume
        # Includes full and partial segments

        V_fin = (
            N_fin
            * N_gap
            * self.H_fin
            * self.l_fin
            * self.t_fin
        )

        m_fin = (
            V_fin * self.rho_al
        )

        # -------------------------------------------------
        # H. Fin heat transfer surface area
        # -------------------------------------------------

        # Both broad faces of all fin segments
        A_fin_broad = (
            2
            * N_fin
            * N_gap
            * self.H_fin
            * self.l_fin
        )

        # Two cut edges per segment
        # Geometric upper estimate
        A_fin_cut_edges = (
            2
            * N_offset_total
            * self.H_fin
            * self.t_fin
        )

        A_fin_total = (
            A_fin_broad + A_fin_cut_edges
        )

        # -------------------------------------------------
        # I. Air-side flow geometry
        # -------------------------------------------------

        A_frontal = (
            self.W_core * self.H_core
        )

        # Average idealized free flow area
        # Does not include manifolds or edge blockage

        A_air_free = (
            self.W_core
            * N_gap
            * self.H_fin
            * fin_open_ratio
        )

        sigma_air = (
            A_air_free / A_frontal
        )

        # Equivalent rectangular channel Dh
        Dh_air = (
            4 * s_clear * self.H_fin
            / (2 * (s_clear + self.H_fin))
        )

        # Geometric core air volume
        V_air_core = (
            A_air_free * self.L_air
        )

        # -------------------------------------------------
        # J. Flat tube external surface area
        # -------------------------------------------------

        A_tube_broad = (
            2
            * self.L_air
            * self.L_oil
            * self.N_tube
        )

        A_tube_side = (
            2
            * self.H_tube
            * self.L_oil
            * self.N_tube
        )

        A_tube_external_total = (
            A_tube_broad + A_tube_side
        )

        # Provisional exposed tube area
        # Broad surfaces assumed covered by fin contact

        A_tube_exposed = A_tube_side

        # Gross air-side heat transfer area
        A_air_heat = (
            A_fin_total + A_tube_exposed
        )

        # -------------------------------------------------
        # K. Core and fin mass-related geometry
        # -------------------------------------------------

        V_core_envelope = (
            self.W_core
            * self.H_core
            * self.L_air
        )

        # -------------------------------------------------
        # L. Return results
        # -------------------------------------------------

        return {

            # Core
            "W_core": self.W_core,
            "H_core": self.H_core,
            "L_air": self.L_air,
            "L_oil": self.L_oil,
            "A_frontal": A_frontal,
            "V_core_envelope": V_core_envelope,
            "H_stack": H_stack,
            "height_error": height_error,

            # Tube
            "h_port": h_port,
            "w_internal": w_internal,
            "w_port": w_port,
            "A_port": A_port,
            "A_tube": A_tube,
            "Dh_oil": Dh_oil,
            "A_oil_total": A_oil_total,

            # Pass
            "tubes_per_pass": tubes_per_pass,
            "N_port_total": N_port_total,
            "N_port_per_pass": N_port_per_pass,
            "A_pass": A_pass,

            # Fin pitch
            "N_fin": N_fin,
            "N_gap": N_gap,
            "actual_fin_width": actual_fin_width,
            "width_error": width_error,
            "s_clear": s_clear,
            "fin_open_ratio": fin_open_ratio,

            # Offset segmentation
            "N_offset_full": N_offset_full,
            "N_offset_partial": N_offset_partial,
            "l_partial": l_partial,
            "N_offset_per_track": N_offset_per_track,
            "N_offset_total": N_offset_total,
            "l_offset_shift": l_offset_shift,

            # Fin material
            "V_fin": V_fin,
            "m_fin": m_fin,

            # Fin area
            "A_fin_broad": A_fin_broad,
            "A_fin_cut_edges": A_fin_cut_edges,
            "A_fin_total": A_fin_total,

            # Air side
            "A_air_free": A_air_free,
            "sigma_air": sigma_air,
            "Dh_air": Dh_air,
            "V_air_core": V_air_core,

            # Tube external area
            "A_tube_broad": A_tube_broad,
            "A_tube_side": A_tube_side,
            "A_tube_exposed": A_tube_exposed,
            "A_tube_external_total": A_tube_external_total,

            # Total heat transfer area
            "A_air_heat": A_air_heat,
        }


# =========================================================
# 7. Output and self-test
# =========================================================

if __name__ == "__main__":

    geometry = CondenserGeometry()

    result = geometry.calculate()

    def show(title, keys):

        print("\n" + title)
        print("-" * 70)

        for key in keys:
            value = result[key]

            if isinstance(value, float):
                print(f"{key:30s}: {value:.8f}")
            else:
                print(f"{key:30s}: {value}")

    print("=" * 70)
    print("CAMS CONDENSER GEOMETRY MODEL V1.2")
    print("OFFSET STRIP FIN")
    print("=" * 70)

    show("[Core Geometry]", [
        "W_core",
        "H_core",
        "L_air",
        "L_oil",
        "A_frontal",
        "V_core_envelope",
        "H_stack",
        "height_error",
    ])

    show("[Oil-side Geometry]", [
        "h_port",
        "w_internal",
        "w_port",
        "A_port",
        "A_tube",
        "Dh_oil",
        "A_oil_total",
    ])

    show("[Flow Pass Geometry]", [
        "tubes_per_pass",
        "N_port_total",
        "N_port_per_pass",
        "A_pass",
    ])

    show("[Fin Pitch Geometry]", [
        "N_fin",
        "N_gap",
        "actual_fin_width",
        "width_error",
        "s_clear",
        "fin_open_ratio",
    ])

    show("[Offset Strip Geometry]", [
        "N_offset_full",
        "N_offset_partial",
        "l_partial",
        "N_offset_per_track",
        "N_offset_total",
        "l_offset_shift",
    ])

    show("[Fin Material]", [
        "V_fin",
        "m_fin",
    ])

    show("[Fin Surface Area]", [
        "A_fin_broad",
        "A_fin_cut_edges",
        "A_fin_total",
    ])

    show("[Air-side Geometry]", [
        "A_air_free",
        "sigma_air",
        "Dh_air",
        "V_air_core",
    ])

    show("[Tube External Area]", [
        "A_tube_broad",
        "A_tube_side",
        "A_tube_exposed",
        "A_tube_external_total",
    ])

    show("[Heat Transfer Area]", [
        "A_air_heat",
    ])

    # -------------------------------------------------
    # Self-tests
    # -------------------------------------------------

    assert math.isclose(
        result["H_stack"],
        geometry.H_core,
        abs_tol=1e-9
    )

    assert math.isclose(
        result["width_error"],
        0.0,
        abs_tol=1e-9
    )

    assert math.isclose(
        result["N_offset_full"] * geometry.l_offset
        + result["l_partial"],
        geometry.l_fin,
        abs_tol=1e-9
    )

    assert result["N_offset_total"] > 0
    assert result["V_fin"] > 0
    assert result["A_fin_total"] > 0

    assert result["A_air_free"] > 0
    assert result["A_air_free"] < result["A_frontal"]

    assert result["A_pass"] > 0
    assert result["Dh_oil"] > 0
    assert result["Dh_air"] > 0

    print("\n" + "=" * 70)
    print("ALL GEOMETRY SELF-TESTS PASSED")
    print("=" * 70)
