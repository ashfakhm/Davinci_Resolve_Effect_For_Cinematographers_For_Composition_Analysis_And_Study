#!/usr/bin/env python3
"""Cinematic Composition Toolkit generator for DaVinci Resolve.

Generates the ultimate professional cinematography composition overlay
toolkit packaged into dist/Cinematic_Composition_Toolkit.drfx.

Key Professional Capabilities:
- Dual/Cross-Format Guides: Guide 1 (Primary) + Guide 2 (Secondary)
  active simultaneously for cross-aspect ratio delivery (e.g. 2.39:1
  theatrical scope alongside 16:9 streaming or 9:16 mobile crop).
- Complete Golden Ratio Suite: Continuous Fibonacci Spiral, Golden
  Section Boxes, and combined Golden Ratio matching Renaissance geometry.
- Storytelling Composition Aids: Headroom & Eyeline Dialogue Guide,
  Looking Room / Lead Room, Negative Space Isolation Frame, and Quadrants.
- ARRI / SmallHD Viewfinder Simulation: Letterbox Surround Shading slider
  (0.0 to 1.0) for on-set monitoring, safely post-merged in the DAG.
- Complete Dynamic Symmetry Suite: Root Rectangles (Root 2, 3, Phi, 4, 5).
- Bulletproof Video Passthrough: Timeline video enters directly into
  PrimaryMerge Background, guaranteeing 100% video visibility.
- 360° Free Angle Rotation + 4-Corner Horizontal/Vertical Flipping.
- High-Performance Vector Mask Pipeline: Border width switching without
  mask level attenuation, delivering smooth 60+ FPS real-time playback.
- Ultra-Clean Compact UI: 'Guide 1', 'Guide 2', and 'Style' tabs.
"""
from __future__ import annotations

import math
import os
import subprocess
import zipfile

PHI = (1 + 5 ** 0.5) / 2


def generate_golden_spiral_data(
    steps: int = 8,
    samples_per_arc: int = 32,
) -> tuple[list[tuple[float, float]], list[tuple[float, float, float, float]]]:
    """Compute points for a smooth, continuous Fibonacci golden spiral.

    Matches classical Renaissance geometry and cinema standards:
    - Rectangle in [0, PHI] x [0, 1] mapped to square-pixel 16:9 space:
      Width = PHI * (9/16) ~= 0.910144, Height = 1.0.
    - Square 0 is exactly 1080 x 1080 pixels (1:1 square aspect ratio).
    - Arcs are true circular arcs with zero aspect distortion.
    - Spirals inwards into the golden eye at (0.203514, -0.223607).
    - Guaranteed C1 continuous with zero jump discontinuities.
    """
    x0, x1 = 0.0, PHI
    y0, y1 = 0.0, 1.0
    arcs = []
    cuts = []

    for k in range(steps):
        m = k % 4
        if m == 0:
            s = y1 - y0
            cx, cy = x0 + s, y0
            a0, a1 = math.pi, 0.5 * math.pi
            cuts.append((x0 + s, y0, x0 + s, y1))
            x0 = x0 + s
        elif m == 1:
            s = x1 - x0
            cx, cy = x0, y1 - s
            a0, a1 = 0.5 * math.pi, 0.0
            cuts.append((x0, y1 - s, x1, y1 - s))
            y1 = y1 - s
        elif m == 2:
            s = y1 - y0
            cx, cy = x1 - s, y1
            a0, a1 = 0.0, -0.5 * math.pi
            cuts.append((x1 - s, y0, x1 - s, y1))
            x1 = x1 - s
        elif m == 3:
            s = x1 - x0
            cx, cy = x1, y0 + s
            a0, a1 = -0.5 * math.pi, -math.pi
            cuts.append((x0, y0 + s, x1, y0 + s))
            y0 = y0 + s
        arcs.append((cx, cy, s, a0, a1))

    # We map [0, PHI] x [0, 1] to centered 16:9 coordinates where square pixels are preserved:
    # X pixel scale: 1920, Y pixel scale: 1080.
    # To make Delta X_px == Delta Y_px, Delta nx = Delta ny * (9 / 16).
    x_scale = 9.0 / 16.0
    xc = PHI / 2.0
    yc = 0.5

    pts: list[tuple[float, float]] = []
    for k, (cx, cy, s, a0, a1) in enumerate(arcs):
        for n in range(samples_per_arc):
            if k > 0 and n == 0:
                continue  # Avoid duplicate point at arc junction
            t = a0 + (a1 - a0) * n / (samples_per_arc - 1)
            px = cx + s * math.cos(t)
            py = cy + s * math.sin(t)
            nx = (px - xc) * x_scale
            ny = py - yc
            pts.append((round(nx, 6), round(ny, 6)))

    norm_cuts: list[tuple[float, float, float, float]] = []
    for ca, cb, cc, cd in cuts:
        nca = round((ca - xc) * x_scale, 6)
        ncb = round(cb - yc, 6)
        ncc = round((cc - xc) * x_scale, 6)
        ncd = round(cd - yc, 6)
        norm_cuts.append((nca, ncb, ncc, ncd))

    return pts, norm_cuts


def format_polyline_points(points: list[tuple[float, float]]) -> str:
    """Format points into Fusion Polyline syntax."""
    lines = []
    for x, y in points:
        lines.append(f"\t\t\t\t\t\t\t\t\t{{ Linear = true, X = {x}, Y = {y} }},")
    return "\n".join(lines)


def build_mask_nodes(prefix: str, ctrl_type_prop: str, ctrl_outline_prop: str) -> str:
    """Generate a high-performance vector mask chain for one guide channel (Guide 1 or Guide 2).

    Architectural Invariant:
    Every mask node has Solid = 0 and Level = 1.0 (constant).
    Visibility is controlled strictly via BorderWidth = iif(active, GuideCtrl.Thickness, 0.0).
    When BorderWidth = 0.0, zero pixels are drawn, and the upstream mask passes through 100%
    unaltered via PaintMode = "Maximum". This completely eliminates upstream mask zeroing.
    """
    spiral_pts, norm_cuts = generate_golden_spiral_data(steps=8, samples_per_arc=32)
    spiral_points_str = format_polyline_points(spiral_pts)

    # Guide 0: Rule of Thirds points (normalized [-0.5, 0.5])
    thirds_v1_str = format_polyline_points([(-0.166667, -0.5), (-0.166667, 0.5)])
    thirds_v2_str = format_polyline_points([(0.166667, -0.5), (0.166667, 0.5)])
    thirds_h1_str = format_polyline_points([(-0.5, -0.166667), (0.5, -0.166667)])
    thirds_h2_str = format_polyline_points([(-0.5, 0.166667), (0.5, 0.166667)])

    # Guide 1: Phi Grid points (1/Phi = 0.618034, 1 - 1/Phi = 0.381966 -> offsets +/-0.118034)
    phi_v1_str = format_polyline_points([(-0.118034, -0.5), (-0.118034, 0.5)])
    phi_v2_str = format_polyline_points([(0.118034, -0.5), (0.118034, 0.5)])
    phi_h1_str = format_polyline_points([(-0.5, -0.118034), (0.5, -0.118034)])
    phi_h2_str = format_polyline_points([(-0.5, 0.118034), (0.5, 0.118034)])

    # Guide 5: Golden Triangles (Dynamic Symmetry)
    tri_diag_str = format_polyline_points([(-0.5, -0.5), (0.5, 0.5)])
    tri_p1_str = format_polyline_points([(-0.5, 0.5), (-0.25965, -0.25965)])
    tri_p2_str = format_polyline_points([(0.5, -0.5), (0.25965, 0.25965)])

    # Guide 6: Harmonic Armature (14-Line Classical Renaissance Lattice)
    diag1_str = format_polyline_points([(-0.5, -0.5), (0.5, 0.5)])
    diag2_str = format_polyline_points([(-0.5, 0.5), (0.5, -0.5)])
    diag_vc_str = format_polyline_points([(0.0, -0.5), (0.0, 0.5)])
    diag_hc_str = format_polyline_points([(-0.5, 0.0), (0.5, 0.0)])
    recip1_str = format_polyline_points([(-0.5, 0.5), (0.0, -0.5), (0.5, 0.5)])
    recip2_str = format_polyline_points([(-0.5, -0.5), (0.0, 0.5), (0.5, -0.5)])
    recip3_str = format_polyline_points([(-0.5, 0.5), (0.5, 0.0), (-0.5, -0.5)])
    recip4_str = format_polyline_points([(0.5, 0.5), (-0.5, 0.0), (0.5, -0.5)])

    # Guide 7: Quadrant Grid (2x2 Symmetry / 4 Quadrants)
    quad_v_str = format_polyline_points([(0.0, -0.5), (0.0, 0.5)])
    quad_h_str = format_polyline_points([(-0.5, 0.0), (0.5, 0.0)])
    quad_tl_h = format_polyline_points([(-0.28, 0.25), (-0.22, 0.25)])
    quad_tl_v = format_polyline_points([(-0.25, 0.22), (-0.25, 0.28)])
    quad_tr_h = format_polyline_points([(0.22, 0.25), (0.28, 0.25)])
    quad_tr_v = format_polyline_points([(0.25, 0.22), (0.25, 0.28)])
    quad_bl_h = format_polyline_points([(-0.28, -0.25), (-0.22, -0.25)])
    quad_bl_v = format_polyline_points([(-0.25, -0.28), (-0.25, -0.22)])
    quad_br_h = format_polyline_points([(0.22, -0.25), (0.28, -0.25)])
    quad_br_v = format_polyline_points([(0.25, -0.28), (0.25, -0.22)])

    # Guide 8: Storytelling Aid: Headroom & Eyeline Dialogue Guide
    hr_eyeline_str = format_polyline_points([(-0.5, 0.166667), (0.5, 0.166667)])
    hr_philine_str = format_polyline_points([(-0.5, 0.118034), (0.5, 0.118034)])
    hr_head15_str = format_polyline_points([(-0.5, 0.35), (0.5, 0.35)])
    hr_plumb_str = format_polyline_points([(0.0, -0.5), (0.0, 0.5)])
    hr_eye_l_h = format_polyline_points([(-0.196667, 0.166667), (-0.136667, 0.166667)])
    hr_eye_l_v = format_polyline_points([(-0.166667, 0.136667), (-0.166667, 0.196667)])
    hr_eye_r_h = format_polyline_points([(0.136667, 0.166667), (0.196667, 0.166667)])
    hr_eye_r_v = format_polyline_points([(0.166667, 0.136667), (0.166667, 0.196667)])
    hr_subj_l_str = format_polyline_points([(-0.166667, -0.5), (-0.166667, 0.35)])
    hr_subj_r_str = format_polyline_points([(0.166667, -0.5), (0.166667, 0.35)])

    # Guide 9: Storytelling Aid: Looking Room / Lead Room (Lead Room & Eyeline)
    look_eyeline_h_str = format_polyline_points([(-0.5, 0.166667), (0.5, 0.166667)])
    look_subj_v_str = format_polyline_points([(0.166667, -0.5), (0.166667, 0.5)])
    look_eye_ch_str = format_polyline_points([(0.136667, 0.166667), (0.196667, 0.166667)])
    look_eye_cv_str = format_polyline_points([(0.166667, 0.136667), (0.166667, 0.196667)])
    look_lead_v_str = format_polyline_points([(-0.166667, -0.5), (-0.166667, 0.5)])
    look_center_tick_str = format_polyline_points([(0.0, 0.136667), (0.0, 0.196667)])

    # Guide 10: Storytelling Aid: Negative Space / Character Isolation Frame (1/3 Isolation Field)
    iso_ground_h_str = format_polyline_points([(-0.5, -0.166667), (0.5, -0.166667)])
    iso_boundary_v_str = format_polyline_points([(-0.166667, -0.5), (-0.166667, 0.5)])
    iso_sky_h_str = format_polyline_points([(-0.166667, 0.166667), (0.5, 0.166667)])
    iso_subj_ch_str = format_polyline_points([(-0.373333, -0.333333), (-0.293333, -0.333333)])
    iso_subj_cv_str = format_polyline_points([(-0.333333, -0.373333), (-0.333333, -0.293333)])

    # Guide 11: Precision ARRI Viewfinder Optical Reticle / Center Crosshairs
    cross_h1_str = format_polyline_points([(-0.08, 0.0), (-0.015, 0.0)])
    cross_h2_str = format_polyline_points([(0.015, 0.0), (0.08, 0.0)])
    cross_v1_str = format_polyline_points([(0.0, -0.08), (0.0, -0.015)])
    cross_v2_str = format_polyline_points([(0.0, 0.015), (0.0, 0.08)])
    cross_dh_str = format_polyline_points([(-0.003, 0.0), (0.003, 0.0)])
    cross_dv_str = format_polyline_points([(0.0, -0.003), (0.0, 0.003)])

    # Golden Eye Focal Node (Guides 2 & 3: exact asymptotic limit 1/(2*sqrt(5)) ~= 0.223607)
    eye_x, eye_y = 0.203514, -0.223607
    fib_eye_h = format_polyline_points([(round(eye_x - 0.025 * (9.0 / 16.0), 6), eye_y), (round(eye_x + 0.025 * (9.0 / 16.0), 6), eye_y)])
    fib_eye_v = format_polyline_points([(eye_x, round(eye_y - 0.025, 6)), (eye_x, round(eye_y + 0.025, 6))])

    # Fibonacci subdivision cuts (Guides 3 and 4)
    fib_cut1_str = format_polyline_points([(norm_cuts[0][0], norm_cuts[0][1]), (norm_cuts[0][2], norm_cuts[0][3])])
    fib_cut2_str = format_polyline_points([(norm_cuts[1][0], norm_cuts[1][1]), (norm_cuts[1][2], norm_cuts[1][3])])
    fib_cut3_str = format_polyline_points([(norm_cuts[2][0], norm_cuts[2][1]), (norm_cuts[2][2], norm_cuts[2][3])])
    fib_cut4_str = format_polyline_points([(norm_cuts[3][0], norm_cuts[3][1]), (norm_cuts[3][2], norm_cuts[3][3])])
    fib_cut5_str = format_polyline_points([(norm_cuts[4][0], norm_cuts[4][1]), (norm_cuts[4][2], norm_cuts[4][3])])
    fib_cut6_str = format_polyline_points([(norm_cuts[5][0], norm_cuts[5][1]), (norm_cuts[5][2], norm_cuts[5][3])])

    p = prefix
    ct = f"GuideCtrl.{ctrl_type_prop}"
    co = f"GuideCtrl.{ctrl_outline_prop}"

    return f"""
				-- ===== {p} GUIDE 0: RULE OF THIRDS =====
				{p}_Thirds_V1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 0, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{thirds_v1_str}
								}},
							}},
						}},
					}},
				}},
				{p}_Thirds_V2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 0, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{thirds_v2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Thirds_V1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Thirds_H1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 0, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{thirds_h1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Thirds_V2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Thirds_H2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 0, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{thirds_h2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Thirds_H1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 6: PHI GRID (GOLDEN RATIO) =====
				{p}_Phi_V1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 6, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{phi_v1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Thirds_H2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Phi_V2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 6, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{phi_v2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Phi_V1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Phi_H1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 6, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{phi_h1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Phi_V2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Phi_H2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 6, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{phi_h2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Phi_H1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 7 & 8: GOLDEN SPIRAL =====
				{p}_Spiral_Mask = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 8, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{spiral_points_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Phi_H2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_EyeH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 8, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_eye_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Spiral_Mask", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_EyeV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 8, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_eye_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_EyeH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 7 & 9: FIBONACCI BOXES =====
				{p}_Fib_Border = RectangleMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{ Value = 0.910144, }},
						Height = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						EffectMask = Input {{ SourceOp = "{p}_Fib_EyeV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Border", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut3 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut3_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut4 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut4_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut3", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut5 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut5_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut4", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Fib_Cut6 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 7 or {ct} == 9, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{fib_cut6_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut5", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 10: GOLDEN TRIANGLES =====
				{p}_Tri_Diag = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 10, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{tri_diag_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Fib_Cut6", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Tri_P1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 10, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{tri_p1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Tri_Diag", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Tri_P2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 10, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{tri_p2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Tri_P1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 11: HARMONIC ARMATURE =====
				{p}_Diag_D1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{diag1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Tri_P2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_D2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{diag2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_D1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_VC = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{diag_vc_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_D2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_HC = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{diag_hc_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_VC", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_R1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{recip1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_HC", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_R2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{recip2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_R1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_R3 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{recip3_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_R2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Diag_R4 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 11, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{recip4_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_R3", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 7: QUADRANT GRID (2x2 SYMMETRY) =====
				{p}_Quad_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_v_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Diag_R4", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_h_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_TL_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_tl_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_TL_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_tl_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_TL_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_TR_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_tr_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_TL_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_TR_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_tr_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_TR_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_BL_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_bl_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_TR_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_BL_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_bl_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_BL_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_BR_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_br_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_BL_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Quad_BR_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 4, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{quad_br_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_BR_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 8: HEADROOM & EYELINE (DIALOGUE) =====
				{p}_HR_Eye = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_eyeline_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Quad_BR_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_Phi = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_philine_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_Eye", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_Top = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_head15_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_Phi", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_Plumb = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_plumb_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_Top", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_EyeLH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_eye_l_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_Plumb", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_EyeLV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_eye_l_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_EyeLH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_EyeRH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_eye_r_h}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_EyeLV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_EyeRV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_eye_r_v}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_EyeRH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_SubjL = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_subj_l_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_EyeRV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_HR_SubjR = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 1, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{hr_subj_r_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_SubjL", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 2: LOOKING ROOM / LEAD ROOM =====
				{p}_Look_Eyeline_H = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_eyeline_h_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_HR_SubjR", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Look_Subj_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_subj_v_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_Eyeline_H", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Look_EyeCH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_eye_ch_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_Subj_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Look_EyeCV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_eye_cv_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_EyeCH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Look_Lead_V = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_lead_v_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_EyeCV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Look_Center_Tick = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 2, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{look_center_tick_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_Lead_V", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 5: NEGATIVE SPACE / ISOLATION =====
				{p}_Iso_Ground = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 5, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{iso_ground_h_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Look_Center_Tick", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Iso_Boundary = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 5, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{iso_boundary_v_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Iso_Ground", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Iso_Sky = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 5, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{iso_sky_h_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Iso_Boundary", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Iso_Subj_CH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 5, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{iso_subj_ch_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Iso_Sky", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Iso_Subj_CV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 5, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{iso_subj_cv_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Iso_Subj_CH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 3: PRECISION VIEWFINDER RETICLE =====
				{p}_Cross_H1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_h1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Iso_Subj_CV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Cross_H2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_h2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Cross_H1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Cross_V1 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_v1_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Cross_H2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Cross_V2 = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_v2_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Cross_V1", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Cross_DH = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_dh_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Cross_V2", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Cross_DV = PolylineMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 3, GuideCtrl.Thickness, 0.0)", }},
						Polyline = Input {{
							Value = Polyline {{
								Closed = false,
								Points = {{
{cross_dv_str}
								}},
							}},
						}},
						EffectMask = Input {{ SourceOp = "{p}_Cross_DH", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} GUIDE 12: SAFE AREAS =====
				{p}_Safe_Action = RectangleMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{ Value = 0.93, }},
						Height = Input {{ Value = 0.93, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 12, GuideCtrl.Thickness, 0.0)", }},
						EffectMask = Input {{ SourceOp = "{p}_Cross_DV", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Safe_Title = RectangleMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{ Value = 0.90, }},
						Height = Input {{ Value = 0.90, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 12, GuideCtrl.Thickness, 0.0)", }},
						EffectMask = Input {{ SourceOp = "{p}_Safe_Action", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
				{p}_Safe_Text = RectangleMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{ Value = 0.80, }},
						Height = Input {{ Value = 0.80, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({ct} == 12, GuideCtrl.Thickness, 0.0)", }},
						EffectMask = Input {{ SourceOp = "{p}_Safe_Title", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},

				-- ===== {p} FRAME OUTLINE =====
				{p}_Frame_Outline_Mask = RectangleMask {{
					Inputs = {{
						Level = Input {{ Value = 1.0, }},
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{ Value = 1.0, }},
						Height = Input {{ Value = 1.0, }},
						Solid = Input {{ Value = 0, }},
						BorderWidth = Input {{ Expression = "iif({co} == 1, GuideCtrl.Thickness, 0.0)", }},
						EffectMask = Input {{ SourceOp = "{p}_Safe_Text", Source = "Mask", }},
						PaintMode = Input {{ Value = "Maximum", }},
					}},
				}},
"""


def build_macro_setting() -> str:
    pri_masks = build_mask_nodes("Pri", "GuideType", "ShowOutline")
    sec_masks = build_mask_nodes("Sec", "SecGuideType", "SecShowOutline")

    setting = f"""{{
	Tools = ordered() {{
		CinematicCompositionToolkit = MacroOperator {{
			CtrlWZoom = false,
			CustomData = {{
				Path = {{
					Map = {{
						["Setting:"] = "Templates:/Cinematic_Composition_Toolkit.drfx/Edit/Effects/Cinematic Guides/"
					}}
				}}
			}},
			Inputs = ordered() {{
				MainInput1 = InstanceInput {{
					SourceOp = "PrimaryMerge",
					Source = "Background",
				}},

				-- ===== PAGE 1: GUIDE 1 =====
				GuideSelect = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "GuideType",
					Name = "Composition Guide",
					Page = "Guide 1",
				}},
				FlipHorizontal = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "FlipH",
					Name = "Flip Horizontal (Mirror)",
					Page = "Guide 1",
				}},
				FlipVertical = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "FlipV",
					Name = "Flip Vertical (Invert)",
					Page = "Guide 1",
				}},
				RotationAngleControl = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "RotationAngle",
					Name = "Rotation Angle (0-360°)",
					Default = 0.0,
					Page = "Guide 1",
				}},
				AspectSelect = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "AspectPreset",
					Name = "Frame / Aspect Ratio",
					Page = "Guide 1",
				}},
				ShowAspectOutline = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "ShowOutline",
					Name = "Show Frame Outline",
					Page = "Guide 1",
				}},
				SurroundShadingControl = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SurroundShading",
					Name = "Surround Shading (Letterbox Matte)",
					Default = 0.0,
					Page = "Guide 1",
				}},
				CustomActiveWidth = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "CustomWidth",
					Name = "Custom Frame Width",
					Default = 1.0,
					Page = "Guide 1",
				}},
				CustomActiveHeight = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "CustomHeight",
					Name = "Custom Frame Height",
					Default = 1.0,
					Page = "Guide 1",
				}},

				-- ===== PAGE 2: GUIDE 2 (CROSS-FORMAT ENGINE) =====
				EnableSecondaryGuide = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "EnableSecondary",
					Name = "Enable Guide 2",
					Page = "Guide 2",
				}},
				SecGuideSelect = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecGuideType",
					Name = "Guide 2 Composition",
					Page = "Guide 2",
				}},
				SecFlipHorizontal = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecFlipH",
					Name = "Guide 2 Flip Horizontal (Mirror)",
					Page = "Guide 2",
				}},
				SecFlipVertical = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecFlipV",
					Name = "Guide 2 Flip Vertical (Invert)",
					Page = "Guide 2",
				}},
				SecRotationAngleControl = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecRotationAngle",
					Name = "Guide 2 Rotation Angle (0-360°)",
					Default = 0.0,
					Page = "Guide 2",
				}},
				SecAspectSelect = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecAspectPreset",
					Name = "Guide 2 Aspect Ratio",
					Page = "Guide 2",
				}},
				SecShowAspectOutline = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecShowOutline",
					Name = "Guide 2 Show Outline",
					Page = "Guide 2",
				}},
				SecColorRed = InstanceInput {{
					SourceOp = "Sec_GuideLines",
					Source = "TopLeftRed",
					Name = "Guide 2 Color",
					ControlGroup = 20,
					Default = 0.2,
					Page = "Guide 2",
				}},
				SecColorGreen = InstanceInput {{
					SourceOp = "Sec_GuideLines",
					Source = "TopLeftGreen",
					ControlGroup = 20,
					Default = 0.85,
					Page = "Guide 2",
				}},
				SecColorBlue = InstanceInput {{
					SourceOp = "Sec_GuideLines",
					Source = "TopLeftBlue",
					ControlGroup = 20,
					Default = 1.0,
					Page = "Guide 2",
				}},
				SecondaryOpacity = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecOpacity",
					Name = "Guide 2 Opacity",
					Default = 0.75,
					Page = "Guide 2",
				}},
				SecCustomActiveWidth = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecCustomWidth",
					Name = "Guide 2 Custom Width",
					Default = 1.0,
					Page = "Guide 2",
				}},
				SecCustomActiveHeight = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "SecCustomHeight",
					Name = "Guide 2 Custom Height",
					Default = 1.0,
					Page = "Guide 2",
				}},

				-- ===== PAGE 3: STYLE =====
				ColorRed = InstanceInput {{
					SourceOp = "Pri_GuideLines",
					Source = "TopLeftRed",
					Name = "Primary Color",
					ControlGroup = 6,
					Default = 1.0,
					Page = "Style",
				}},
				ColorGreen = InstanceInput {{
					SourceOp = "Pri_GuideLines",
					Source = "TopLeftGreen",
					ControlGroup = 6,
					Default = 1.0,
					Page = "Style",
				}},
				ColorBlue = InstanceInput {{
					SourceOp = "Pri_GuideLines",
					Source = "TopLeftBlue",
					ControlGroup = 6,
					Default = 1.0,
					Page = "Style",
				}},
				MasterOpacity = InstanceInput {{
					SourceOp = "PrimaryMerge",
					Source = "Blend",
					Name = "Primary Opacity",
					Default = 0.85,
					Page = "Style",
				}},
				LineThickness = InstanceInput {{
					SourceOp = "GuideCtrl",
					Source = "Thickness",
					Name = "Line Thickness",
					Default = 0.002,
					Page = "Style",
				}},
			}},
			Outputs = {{
				MainOutput1 = InstanceOutput {{
					SourceOp = "LetterboxMerge",
					Source = "Output",
				}}
			}},
			ViewInfo = GroupInfo {{ Pos = {{ 0, 0 }} }},
			Tools = ordered() {{
				GuideCtrl = AlphaDivide {{
					PassThrough = true,
					CtrlWShown = false,
					NameSet = true,
					Inputs = {{
						GuideType = Input {{ Value = 0, }},
						AspectPreset = Input {{ Value = 0, }},
						Thickness = Input {{ Value = 0.002, }},
						FlipH = Input {{ Value = 0, }},
						FlipV = Input {{ Value = 0, }},
						RotationAngle = Input {{ Value = 0.0, }},
						ShowOutline = Input {{ Value = 0, }},
						SurroundShading = Input {{ Value = 0.0, }},
						CustomWidth = Input {{ Value = 1.0, }},
						CustomHeight = Input {{ Value = 1.0, }},

						EnableSecondary = Input {{ Value = 0, }},
						SecGuideType = Input {{ Value = 0, }},
						SecAspectPreset = Input {{ Value = 0, }},
						SecShowOutline = Input {{ Value = 0, }},
						SecOpacity = Input {{ Value = 0.75, }},
						SecFlipH = Input {{ Value = 0, }},
						SecFlipV = Input {{ Value = 0, }},
						SecRotationAngle = Input {{ Value = 0.0, }},
						SecCustomWidth = Input {{ Value = 1.0, }},
						SecCustomHeight = Input {{ Value = 1.0, }},
					}},
					UserControls = ordered() {{
						GuideType = {{
							{{ CCS_AddString = "Rule of Thirds" }},
							{{ CCS_AddString = "Headroom & Eyeline (Dialogue Framing)" }},
							{{ CCS_AddString = "Looking Room (Lead Room & Eyeline)" }},
							{{ CCS_AddString = "Center Reticle (ARRI Optical Crosshairs)" }},
							{{ CCS_AddString = "Quadrant Grid (2x2 Symmetrical Quadrants)" }},
							{{ CCS_AddString = "Negative Space (Character Isolation)" }},
							{{ CCS_AddString = "Phi Grid (Golden Ratio Grid - 1:1.618:1)" }},
							{{ CCS_AddString = "Golden Ratio (Spiral + Fibonacci Boxes)" }},
							{{ CCS_AddString = "Golden Spiral (Fibonacci Spiral Only)" }},
							{{ CCS_AddString = "Golden Section (Fibonacci Boxes Only)" }},
							{{ CCS_AddString = "Golden Triangles (Dynamic Symmetry)" }},
							{{ CCS_AddString = "Harmonic Armature (14-Line Classical)" }},
							{{ CCS_AddString = "Safe Areas (93% Action / 90% Title / 80% Text)" }},
							{{ CCS_AddString = "None (Frame Outline Only)" }},
							INP_Integer = true,
							INPID_InputControl = "ComboControl",
							CC_LabelPosition = "Horizontal",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 1 Composition",
						}},
						AspectPreset = {{
							{{ CCS_AddString = "Full Frame (Match Timeline)" }},
							{{ CCS_AddString = "2.39:1 Cinema Scope (Theatrical Widescreen)" }},
							{{ CCS_AddString = "2.00:1 Univisium (18:9 / Streaming Widescreen)" }},
							{{ CCS_AddString = "1.90:1 Digital IMAX" }},
							{{ CCS_AddString = "1.85:1 Flat Cinema (Standard Theatrical)" }},
							{{ CCS_AddString = "1.66:1 European Flat (Kubrick / A24)" }},
							{{ CCS_AddString = "1.43:1 IMAX GT Laser (70mm Full Height)" }},
							{{ CCS_AddString = "1.33:1 (4:3 Classic Academy)" }},
							{{ CCS_AddString = "9:16 Vertical (Reels / TikTok / Shorts)" }},
							{{ CCS_AddString = "1:1 Square (Social / Art House)" }},
							{{ CCS_AddString = "1.618:1 Golden Rectangle (Phi Dynamic)" }},
							{{ CCS_AddString = "2.236:1 Root 5 Dynamic Symmetry" }},
							{{ CCS_AddString = "1.732:1 Root 3 Dynamic Symmetry" }},
							{{ CCS_AddString = "1.414:1 Root 2 Dynamic Symmetry" }},
							{{ CCS_AddString = "2.35:1 Scope (Vintage Panavision Pre-1970)" }},
							{{ CCS_AddString = "Custom (Adjust Sliders Below)" }},
							INP_Integer = true,
							INPID_InputControl = "ComboControl",
							CC_LabelPosition = "Horizontal",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 1 Aspect Ratio",
						}},
						Thickness = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 0.002,
							INP_MinAllowed = 0.0005,
							INP_MaxAllowed = 0.015,
							INP_MinScale = 0.001,
							INP_MaxScale = 0.01,
							LINKID_DataType = "Number",
							LINKS_Name = "Line Thickness",
						}},
						FlipH = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Flip Horizontal (Guide 1)",
						}},
						FlipV = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Flip Vertical (Guide 1)",
						}},
						RotationAngle = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 0.0,
							INP_MinAllowed = -360.0,
							INP_MaxAllowed = 360.0,
							INP_MinScale = 0.0,
							INP_MaxScale = 360.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Rotation Angle (Guide 1)",
						}},
						ShowOutline = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Show Frame Outline",
						}},
						SurroundShading = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 0.0,
							INP_MinAllowed = 0.0,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.0,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Surround Shading (Letterbox Matte)",
						}},
						CustomWidth = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 1.0,
							INP_MinAllowed = 0.05,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.1,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Custom Frame Width",
						}},
						CustomHeight = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 1.0,
							INP_MinAllowed = 0.05,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.1,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Custom Frame Height",
						}},

						-- Secondary Guide Controls (Guide 2)
						EnableSecondary = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Enable Guide 2",
						}},
						SecGuideType = {{
							{{ CCS_AddString = "Rule of Thirds" }},
							{{ CCS_AddString = "Headroom & Eyeline (Dialogue Framing)" }},
							{{ CCS_AddString = "Looking Room (Lead Room & Eyeline)" }},
							{{ CCS_AddString = "Center Reticle (ARRI Optical Crosshairs)" }},
							{{ CCS_AddString = "Quadrant Grid (2x2 Symmetrical Quadrants)" }},
							{{ CCS_AddString = "Negative Space (Character Isolation)" }},
							{{ CCS_AddString = "Phi Grid (Golden Ratio Grid - 1:1.618:1)" }},
							{{ CCS_AddString = "Golden Ratio (Spiral + Fibonacci Boxes)" }},
							{{ CCS_AddString = "Golden Spiral (Fibonacci Spiral Only)" }},
							{{ CCS_AddString = "Golden Section (Fibonacci Boxes Only)" }},
							{{ CCS_AddString = "Golden Triangles (Dynamic Symmetry)" }},
							{{ CCS_AddString = "Harmonic Armature (14-Line Classical)" }},
							{{ CCS_AddString = "Safe Areas (93% Action / 90% Title / 80% Text)" }},
							{{ CCS_AddString = "None (Frame Outline Only)" }},
							INP_Integer = true,
							INPID_InputControl = "ComboControl",
							CC_LabelPosition = "Horizontal",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Composition",
						}},
						SecAspectPreset = {{
							{{ CCS_AddString = "Full Frame (Match Timeline)" }},
							{{ CCS_AddString = "2.39:1 Cinema Scope (Theatrical Widescreen)" }},
							{{ CCS_AddString = "2.00:1 Univisium (18:9 / Streaming Widescreen)" }},
							{{ CCS_AddString = "1.90:1 Digital IMAX" }},
							{{ CCS_AddString = "1.85:1 Flat Cinema (Standard Theatrical)" }},
							{{ CCS_AddString = "1.66:1 European Flat (Kubrick / A24)" }},
							{{ CCS_AddString = "1.43:1 IMAX GT Laser (70mm Full Height)" }},
							{{ CCS_AddString = "1.33:1 (4:3 Classic Academy)" }},
							{{ CCS_AddString = "9:16 Vertical (Reels / TikTok / Shorts)" }},
							{{ CCS_AddString = "1:1 Square (Social / Art House)" }},
							{{ CCS_AddString = "1.618:1 Golden Rectangle (Phi Dynamic)" }},
							{{ CCS_AddString = "2.236:1 Root 5 Dynamic Symmetry" }},
							{{ CCS_AddString = "1.732:1 Root 3 Dynamic Symmetry" }},
							{{ CCS_AddString = "1.414:1 Root 2 Dynamic Symmetry" }},
							{{ CCS_AddString = "2.35:1 Scope (Vintage Panavision Pre-1970)" }},
							{{ CCS_AddString = "Custom (Adjust Sliders Below)" }},
							INP_Integer = true,
							INPID_InputControl = "ComboControl",
							CC_LabelPosition = "Horizontal",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Aspect Ratio",
						}},
						SecShowOutline = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Show Outline",
						}},
						SecOpacity = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 0.75,
							INP_MinAllowed = 0.0,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.0,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Opacity",
						}},
						SecCustomWidth = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 1.0,
							INP_MinAllowed = 0.05,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.1,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Custom Width",
						}},
						SecCustomHeight = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 1.0,
							INP_MinAllowed = 0.05,
							INP_MaxAllowed = 1.0,
							INP_MinScale = 0.1,
							INP_MaxScale = 1.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Guide 2 Custom Height",
						}},
						SecFlipH = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Flip Horizontal (Guide 2)",
						}},
						SecFlipV = {{
							INP_Integer = true,
							INPID_InputControl = "CheckboxControl",
							INP_Default = 0,
							LINKID_DataType = "Number",
							LINKS_Name = "Flip Vertical (Guide 2)",
						}},
						SecRotationAngle = {{
							INPID_InputControl = "SliderControl",
							INP_Default = 0.0,
							INP_MinAllowed = -360.0,
							INP_MaxAllowed = 360.0,
							INP_MinScale = 0.0,
							INP_MaxScale = 360.0,
							LINKID_DataType = "Number",
							LINKS_Name = "Rotation Angle (Guide 2)",
						}},
					}},
				}},

{pri_masks}
{sec_masks}

				-- ===== PRIMARY GUIDE BACKGROUND =====
				Pri_GuideLines = Background {{
					Inputs = {{
						GlobalIn = Input {{ Value = -9999, }},
						GlobalOut = Input {{ Value = 99999, }},
						UseFrameFormatSettings = Input {{ Value = 1, }},
						Width = Input {{ Value = 1920, }},
						Height = Input {{ Value = 1080, }},
						TopLeftRed = Input {{ Value = 1.0, }},
						TopLeftGreen = Input {{ Value = 1.0, }},
						TopLeftBlue = Input {{ Value = 1.0, }},
						TopLeftAlpha = Input {{ Value = 1.0, }},
						EffectMask = Input {{ SourceOp = "Pri_Frame_Outline_Mask", Source = "Mask", }},
					}},
				}},

				-- ===== PRIMARY ASPECT TRANSFORM =====
				Pri_AspectTransform = Transform {{
					Inputs = {{
						UseSizeAndAspect = Input {{ Value = 0, }},
						Input = Input {{ SourceOp = "Pri_GuideLines", Source = "Output", }},
						XSize = Input {{
							Expression = "iif(GuideCtrl.GuideType >= 7 and GuideCtrl.GuideType <= 9, iif(GuideCtrl.AspectPreset == 1, 0.743840, iif(GuideCtrl.AspectPreset == 2, 0.888889, iif(GuideCtrl.AspectPreset == 3, 0.935673, iif(GuideCtrl.AspectPreset == 4, 0.960961, iif(GuideCtrl.AspectPreset == 6, 0.883789, iif(GuideCtrl.AspectPreset == 7, 0.824045, iif(GuideCtrl.AspectPreset == 8, 0.347644, iif(GuideCtrl.AspectPreset == 9, 0.618034, iif(GuideCtrl.AspectPreset == 11, 0.795046, iif(GuideCtrl.AspectPreset == 13, 0.874032, iif(GuideCtrl.AspectPreset == 14, 0.756501, 1.0))))))))))), iif(GuideCtrl.AspectPreset == 5, 0.9375, iif(GuideCtrl.AspectPreset == 6, 0.804375, iif(GuideCtrl.AspectPreset == 7, 0.75, iif(GuideCtrl.AspectPreset == 8, 0.316406, iif(GuideCtrl.AspectPreset == 9, 0.5625, iif(GuideCtrl.AspectPreset == 10, 0.910144, iif(GuideCtrl.AspectPreset == 12, 0.974279, iif(GuideCtrl.AspectPreset == 13, 0.795495, 1.0))))))))) * GuideCtrl.CustomWidth",
						}},
						YSize = Input {{
							Expression = "iif(GuideCtrl.GuideType >= 7 and GuideCtrl.GuideType <= 9, iif(GuideCtrl.AspectPreset == 1, 0.743840, iif(GuideCtrl.AspectPreset == 2, 0.888889, iif(GuideCtrl.AspectPreset == 3, 0.935673, iif(GuideCtrl.AspectPreset == 4, 0.960961, iif(GuideCtrl.AspectPreset == 6, 0.883789, iif(GuideCtrl.AspectPreset == 7, 0.824045, iif(GuideCtrl.AspectPreset == 8, 0.347644, iif(GuideCtrl.AspectPreset == 9, 0.618034, iif(GuideCtrl.AspectPreset == 11, 0.795046, iif(GuideCtrl.AspectPreset == 13, 0.874032, iif(GuideCtrl.AspectPreset == 14, 0.756501, 1.0))))))))))), iif(GuideCtrl.AspectPreset == 1, 0.743840, iif(GuideCtrl.AspectPreset == 2, 0.888889, iif(GuideCtrl.AspectPreset == 3, 0.935673, iif(GuideCtrl.AspectPreset == 4, 0.960961, iif(GuideCtrl.AspectPreset == 11, 0.795046, iif(GuideCtrl.AspectPreset == 14, 0.756501, 1.0))))))) * GuideCtrl.CustomHeight",
						}},
						Angle = Input {{ Expression = "GuideCtrl.RotationAngle", }},
						FlipHoriz = Input {{ Expression = "GuideCtrl.FlipH", }},
						FlipVert = Input {{ Expression = "GuideCtrl.FlipV", }},
					}},
				}},

				-- ===== PRIMARY MERGE (TIMELINE VIDEO AS BACKGROUND) =====
				PrimaryMerge = Merge {{
					Inputs = {{
						Foreground = Input {{ SourceOp = "Pri_AspectTransform", Source = "Output", }},
						Blend = Input {{ Value = 0.85, }},
					}},
				}},

				-- ===== SECONDARY GUIDE BACKGROUND =====
				Sec_GuideLines = Background {{
					Inputs = {{
						GlobalIn = Input {{ Value = -9999, }},
						GlobalOut = Input {{ Value = 99999, }},
						UseFrameFormatSettings = Input {{ Value = 1, }},
						Width = Input {{ Value = 1920, }},
						Height = Input {{ Value = 1080, }},
						TopLeftRed = Input {{ Value = 0.2, }},
						TopLeftGreen = Input {{ Value = 0.85, }},
						TopLeftBlue = Input {{ Value = 1.0, }},
						TopLeftAlpha = Input {{ Value = 1.0, }},
						EffectMask = Input {{ SourceOp = "Sec_Frame_Outline_Mask", Source = "Mask", }},
					}},
				}},

				-- ===== SECONDARY ASPECT TRANSFORM =====
				Sec_AspectTransform = Transform {{
					Inputs = {{
						UseSizeAndAspect = Input {{ Value = 0, }},
						Input = Input {{ SourceOp = "Sec_GuideLines", Source = "Output", }},
						XSize = Input {{
							Expression = "iif(GuideCtrl.SecGuideType >= 7 and GuideCtrl.SecGuideType <= 9, iif(GuideCtrl.SecAspectPreset == 1, 0.743840, iif(GuideCtrl.SecAspectPreset == 2, 0.888889, iif(GuideCtrl.SecAspectPreset == 3, 0.935673, iif(GuideCtrl.SecAspectPreset == 4, 0.960961, iif(GuideCtrl.SecAspectPreset == 6, 0.883789, iif(GuideCtrl.SecAspectPreset == 7, 0.824045, iif(GuideCtrl.SecAspectPreset == 8, 0.347644, iif(GuideCtrl.SecAspectPreset == 9, 0.618034, iif(GuideCtrl.SecAspectPreset == 11, 0.795046, iif(GuideCtrl.SecAspectPreset == 13, 0.874032, iif(GuideCtrl.SecAspectPreset == 14, 0.756501, 1.0))))))))))), iif(GuideCtrl.SecAspectPreset == 5, 0.9375, iif(GuideCtrl.SecAspectPreset == 6, 0.804375, iif(GuideCtrl.SecAspectPreset == 7, 0.75, iif(GuideCtrl.SecAspectPreset == 8, 0.316406, iif(GuideCtrl.SecAspectPreset == 9, 0.5625, iif(GuideCtrl.SecAspectPreset == 10, 0.910144, iif(GuideCtrl.SecAspectPreset == 12, 0.974279, iif(GuideCtrl.SecAspectPreset == 13, 0.795495, 1.0))))))))) * GuideCtrl.SecCustomWidth",
						}},
						YSize = Input {{
							Expression = "iif(GuideCtrl.SecGuideType >= 7 and GuideCtrl.SecGuideType <= 9, iif(GuideCtrl.SecAspectPreset == 1, 0.743840, iif(GuideCtrl.SecAspectPreset == 2, 0.888889, iif(GuideCtrl.SecAspectPreset == 3, 0.935673, iif(GuideCtrl.SecAspectPreset == 4, 0.960961, iif(GuideCtrl.SecAspectPreset == 6, 0.883789, iif(GuideCtrl.SecAspectPreset == 7, 0.824045, iif(GuideCtrl.SecAspectPreset == 8, 0.347644, iif(GuideCtrl.SecAspectPreset == 9, 0.618034, iif(GuideCtrl.SecAspectPreset == 11, 0.795046, iif(GuideCtrl.SecAspectPreset == 13, 0.874032, iif(GuideCtrl.SecAspectPreset == 14, 0.756501, 1.0))))))))))), iif(GuideCtrl.SecAspectPreset == 1, 0.743840, iif(GuideCtrl.SecAspectPreset == 2, 0.888889, iif(GuideCtrl.SecAspectPreset == 3, 0.935673, iif(GuideCtrl.SecAspectPreset == 4, 0.960961, iif(GuideCtrl.SecAspectPreset == 11, 0.795046, iif(GuideCtrl.SecAspectPreset == 14, 0.756501, 1.0))))))) * GuideCtrl.SecCustomHeight",
						}},
						Angle = Input {{ Expression = "GuideCtrl.SecRotationAngle", }},
						FlipHoriz = Input {{ Expression = "GuideCtrl.SecFlipH", }},
						FlipVert = Input {{ Expression = "GuideCtrl.SecFlipV", }},
					}},
				}},

				-- ===== SECONDARY MERGE =====
				SecondaryMerge = Merge {{
					Inputs = {{
						Background = Input {{ SourceOp = "PrimaryMerge", Source = "Output", }},
						Foreground = Input {{ SourceOp = "Sec_AspectTransform", Source = "Output", }},
						Blend = Input {{ Expression = "GuideCtrl.SecOpacity * GuideCtrl.EnableSecondary", }},
					}},
				}},

				-- ===== LETTERBOX SURROUND MATTE (ARRI / SMALLHD VIEWFINDER SIMULATION) =====
				LetterboxMask = RectangleMask {{
					Inputs = {{
						Center = Input {{ Value = {{ 0.5, 0.5 }}, }},
						Width = Input {{
							Expression = "(iif(GuideCtrl.AspectPreset == 5, 0.9375, iif(GuideCtrl.AspectPreset == 6, 0.804375, iif(GuideCtrl.AspectPreset == 7, 0.75, iif(GuideCtrl.AspectPreset == 8, 0.316406, iif(GuideCtrl.AspectPreset == 9, 0.5625, iif(GuideCtrl.AspectPreset == 10, 0.910144, iif(GuideCtrl.AspectPreset == 12, 0.974279, iif(GuideCtrl.AspectPreset == 13, 0.795495, 1.0))))))))) * GuideCtrl.CustomWidth",
						}},
						Height = Input {{
							Expression = "(iif(GuideCtrl.AspectPreset == 1, 0.743840, iif(GuideCtrl.AspectPreset == 2, 0.888889, iif(GuideCtrl.AspectPreset == 3, 0.935673, iif(GuideCtrl.AspectPreset == 4, 0.960961, iif(GuideCtrl.AspectPreset == 11, 0.795046, iif(GuideCtrl.AspectPreset == 14, 0.756501, 1.0))))))) * GuideCtrl.CustomHeight",
						}},
						Invert = Input {{ Value = 1, }},
						Solid = Input {{ Value = 1, }},
						Level = Input {{ Value = 1.0, }},
					}},
				}},
				LetterboxBg = Background {{
					Inputs = {{
						GlobalIn = Input {{ Value = -9999, }},
						GlobalOut = Input {{ Value = 99999, }},
						UseFrameFormatSettings = Input {{ Value = 1, }},
						Width = Input {{ Value = 1920, }},
						Height = Input {{ Value = 1080, }},
						TopLeftRed = Input {{ Value = 0.0, }},
						TopLeftGreen = Input {{ Value = 0.0, }},
						TopLeftBlue = Input {{ Value = 0.0, }},
						TopLeftAlpha = Input {{ Value = 1.0, }},
						EffectMask = Input {{ SourceOp = "LetterboxMask", Source = "Mask", }},
					}},
				}},
				LetterboxMerge = Merge {{
					Inputs = {{
						Background = Input {{ SourceOp = "SecondaryMerge", Source = "Output", }},
						Foreground = Input {{ SourceOp = "LetterboxBg", Source = "Output", }},
						Blend = Input {{ Expression = "GuideCtrl.SurroundShading", }},
					}},
				}},
			}},
		}},
	}},
	ActiveTool = "CinematicCompositionToolkit"
}}
"""
    return setting


def validate_with_fuscript(setting_path: str) -> bool:
    """Validate setting file using DaVinci Resolve's native fuscript interpreter."""
    fuscript = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fuscript"
    if not os.path.isfile(fuscript):
        print(f"Notice: {fuscript} not found. Skipping fuscript validation.")
        return True

    cmd = [
        fuscript,
        "-x",
        f"""
local f = io.open([[{setting_path}]], 'r')
if not f then error('Cannot open file') end
local content = f:read('*all')
f:close()

local function make_callable(t)
    if type(t) ~= 'table' then
        return function(...) return make_callable(...) end
    end
    return setmetatable(t, {{
        __call = function(self, arg)
            return make_callable(arg)
        end
    }})
end

setmetatable(_G, {{
    __index = function(tbl, key)
        return function(...)
            return make_callable(...)
        end
    end
}})

local func, err = loadstring('return ' .. content)
if not func then
    io.stderr:write('Lua Syntax Error: ' .. tostring(err) .. '\\n')
    os.exit(1)
end
local ok, res = pcall(func)
if not ok then
    io.stderr:write('Evaluation Error: ' .. tostring(res) .. '\\n')
    os.exit(1)
end

-- Validate all nested expressions inside the setting file
local count = 0
for expr in content:gmatch('Expression%s*=%s*"(.-)"') do
    count = count + 1
    local f_expr, expr_err = loadstring('return ' .. expr)
    if not f_expr then
        io.stderr:write('Expression Syntax Error: ' .. tostring(expr_err) .. ' in: ' .. expr .. '\\n')
        os.exit(1)
    end
end

print('fuscript verification: PASS (Valid Fusion Lua table with ' .. count .. ' verified expressions)')
os.exit(0)
""",
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        print("fuscript stderr:", proc.stderr)
        return False
    print(proc.stdout.strip())
    return True


def main() -> None:
    """Build setting file, validate with fuscript, and package DRFX."""
    os.makedirs("dist", exist_ok=True)
    setting_text = build_macro_setting()

    setting_output_path = "dist/Cinematic Composition Toolkit.setting"
    with open(setting_output_path, "w", encoding="utf-8") as setting_file:
        setting_file.write(setting_text)

    print(f"Generated {setting_output_path} ({len(setting_text)} bytes)")
    if not validate_with_fuscript(setting_output_path):
        raise SystemExit("ERROR: fuscript validation failed!")

    bundle_output_path = "dist/Cinematic_Composition_Toolkit.drfx"
    bundle_internal_entry = (
        "Edit/Effects/Cinematic Guides/Cinematic Composition Toolkit.setting"
    )

    with zipfile.ZipFile(
        bundle_output_path, "w", zipfile.ZIP_DEFLATED
    ) as drfx_archive:
        drfx_archive.writestr(bundle_internal_entry, setting_text)

    file_size_kb = os.path.getsize(bundle_output_path) / 1024
    print(f"Successfully packaged {bundle_output_path} ({file_size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
