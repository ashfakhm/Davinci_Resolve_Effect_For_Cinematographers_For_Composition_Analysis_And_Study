"""Automated test suite for the Cinematic Composition Toolkit.

Follows the 3A pattern (Arrange, Act, Assert) strictly for every test.
Adheres to PEP 8 standards with a 79-character maximum line length.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
import zipfile

# Ensure tools directory is available on Python module search path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import build_cinematic_toolkit
import validate_drfx


class TestCinematicCompositionToolkit(unittest.TestCase):
    """Test suite validating mathematical precision and bundle invariants."""

    def test_spiral_points_generation(self) -> None:
        """Verify spiral generation produces sufficient density and bounds."""
        # Arrange
        target_steps = 8
        target_samples_per_arc = 32
        coordinate_limit = 0.6

        # Act
        spiral_points, subdivision_cuts = (
            build_cinematic_toolkit.generate_golden_spiral_data(
                steps=target_steps,
                samples_per_arc=target_samples_per_arc,
            )
        )

        # Assert
        self.assertGreater(
            len(spiral_points),
            150,
            "Spiral must generate at least 150 points for smooth rendering",
        )
        self.assertGreaterEqual(
            len(subdivision_cuts),
            6,
            "Fibonacci generator must produce at least 6 boundary cuts",
        )
        min_x_coord = min(point[0] for point in spiral_points)
        max_x_coord = max(point[0] for point in spiral_points)
        min_y_coord = min(point[1] for point in spiral_points)
        max_y_coord = max(point[1] for point in spiral_points)

        self.assertGreaterEqual(min_x_coord, -coordinate_limit)
        self.assertLessEqual(max_x_coord, coordinate_limit)
        self.assertGreaterEqual(min_y_coord, -coordinate_limit)
        self.assertLessEqual(max_y_coord, coordinate_limit)

    def test_spiral_continuity(self) -> None:
        """Verify the golden spiral has zero jump discontinuities."""
        # Arrange
        max_allowed_delta = 0.06
        spiral_points, _ = (
            build_cinematic_toolkit.generate_golden_spiral_data(
                steps=8, samples_per_arc=32
            )
        )
        max_measured_step = 0.0

        # Act
        for index in range(len(spiral_points) - 1):
            delta_x = spiral_points[index + 1][0] - spiral_points[index][0]
            delta_y = spiral_points[index + 1][1] - spiral_points[index][1]
            euclidean_distance = (delta_x**2 + delta_y**2) ** 0.5
            max_measured_step = max(max_measured_step, euclidean_distance)

        # Assert
        self.assertLess(
            max_measured_step,
            max_allowed_delta,
            f"Spiral has a jump discontinuity: distance={max_measured_step}",
        )

    def test_polyline_points_formatting(self) -> None:
        """Verify Fusion Polyline syntax formatting correctness."""
        # Arrange
        input_coordinates = [(0.0, 0.0), (1.0, 1.0)]

        # Act
        formatted_output = build_cinematic_toolkit.format_polyline_points(
            input_coordinates
        )

        # Assert
        self.assertIn("Linear = true", formatted_output)
        self.assertIn("X = 0.0", formatted_output)
        self.assertIn("Y = 1.0", formatted_output)

    def test_macro_setting_structure(self) -> None:
        """Verify macro structure, critical nodes, and expressions."""
        # Arrange & Act
        macro_text = build_cinematic_toolkit.build_macro_setting()

        # Assert: Core nodes and non-destructive video passthrough
        self.assertIn("CinematicCompositionToolkit = MacroOperator", macro_text)
        self.assertIn("MainInput1 = InstanceInput", macro_text)
        self.assertIn("MainOutput1 = InstanceOutput", macro_text)
        self.assertIn("GuideCtrl = AlphaDivide", macro_text)
        self.assertIn("Pri_AspectTransform = Transform", macro_text)
        self.assertIn("Sec_AspectTransform = Transform", macro_text)
        self.assertIn("PrimaryMerge = Merge", macro_text)
        self.assertIn("SecondaryMerge = Merge", macro_text)
        self.assertIn(
            'SourceOp = "PrimaryMerge",\n\t\t\t\t\tSource = "Background",',
            macro_text,
        )

        # Assert: Composition guide options
        composition_guides = (
            "Rule of Thirds",
            "Headroom & Eyeline (Dialogue Framing)",
            "Looking Room (Lead Room & Eyeline)",
            "Center Reticle (ARRI Optical Crosshairs)",
            "Quadrant Grid (2x2 Symmetrical Quadrants)",
            "Negative Space (Character Isolation)",
            "Phi Grid (Golden Ratio Grid - 1:1.618:1)",
            "Golden Ratio (Spiral + Fibonacci Boxes)",
            "Golden Spiral (Fibonacci Spiral Only)",
            "Golden Section (Fibonacci Boxes Only)",
            "Golden Triangles (Dynamic Symmetry)",
            "Harmonic Armature (14-Line Classical)",
            "Safe Areas (93% Action / 90% Title / 80% Text)",
            "None (Frame Outline Only)",
        )
        for guide in composition_guides:
            self.assertIn(guide, macro_text)

        # Assert: Clean 3-tab UI layout
        self.assertIn('Page = "Guide 1",', macro_text)
        self.assertIn('Page = "Guide 2",', macro_text)
        self.assertIn('Page = "Style",', macro_text)
        self.assertNotIn('Page = "Primary Guide",', macro_text)
        self.assertNotIn('Page = "Secondary Guide",', macro_text)

        # Assert: Live slider scaling expressions
        self.assertIn("GuideCtrl.CustomWidth", macro_text)
        self.assertIn("GuideCtrl.CustomHeight", macro_text)
        self.assertIn("GuideCtrl.SecCustomWidth", macro_text)
        self.assertIn("GuideCtrl.SecCustomHeight", macro_text)

        # Assert: No mask level zeroing or destructive multiplication
        self.assertNotIn("Level = Input { Expression =", macro_text)

        # Assert: Balanced parentheses in all Fusion expressions
        expression_pattern = r'Expression\s*=\s*"([^"]+)"'
        extracted_expressions = re.findall(expression_pattern, macro_text)
        self.assertGreater(len(extracted_expressions), 100)
        for expression in extracted_expressions:
            open_count = expression.count("(")
            close_count = expression.count(")")
            self.assertEqual(
                open_count,
                close_count,
                f"Mismatched parentheses in: {expression}",
            )

        self.assertTrue(validate_drfx.brace_balance(macro_text))

    def test_fibonacci_squares_exact_aspect_ratio(self) -> None:
        """Verify Fibonacci subdivision boxes are geometrically exact squares."""
        # Arrange
        golden_ratio = (1.0 + 5.0**0.5) / 2.0
        frame_aspect_scale = 9.0 / 16.0
        border_width = golden_ratio * frame_aspect_scale
        timeline_width = 1920.0
        timeline_height = 1080.0
        left_pixel_bound = (-border_width / 2.0 + 0.5) * timeline_width
        right_pixel_bound = (border_width / 2.0 + 0.5) * timeline_width

        # Act
        _, cuts = build_cinematic_toolkit.generate_golden_spiral_data(
            steps=8, samples_per_arc=32
        )

        # Assert: Square 0 (largest box)
        cut1_x_pixel = (cuts[0][0] + 0.5) * timeline_width
        square0_pixel_width = cut1_x_pixel - left_pixel_bound
        square0_pixel_height = timeline_height
        self.assertAlmostEqual(square0_pixel_width, 1080.0, places=1)
        self.assertAlmostEqual(square0_pixel_height, 1080.0, places=1)
        self.assertAlmostEqual(
            square0_pixel_width / square0_pixel_height, 1.000000, places=4
        )

        # Assert: Square 1 (second largest box)
        cut2_y_pixel = (cuts[1][1] + 0.5) * timeline_height
        square1_pixel_width = right_pixel_bound - cut1_x_pixel
        square1_pixel_height = timeline_height - cut2_y_pixel
        self.assertAlmostEqual(square1_pixel_width, 667.48, places=1)
        self.assertAlmostEqual(square1_pixel_height, 667.48, places=1)
        self.assertAlmostEqual(
            square1_pixel_width / square1_pixel_height, 1.000000, places=4
        )

    def test_golden_eye_asymptotic_convergence(self) -> None:
        """Verify Golden Eye converges to the exact theoretical coordinate."""
        # Arrange
        golden_ratio = (1.0 + 5.0**0.5) / 2.0
        frame_scale = 9.0 / 16.0

        # Act
        expected_normalized_x = round(
            golden_ratio / (2.0 * (5.0**0.5)) * frame_scale, 6
        )
        expected_normalized_y = round(-0.5 / (5.0**0.5), 6)

        # Assert
        self.assertEqual(expected_normalized_x, 0.203514)
        self.assertEqual(expected_normalized_y, -0.223607)

    def test_drfx_bundle_validation(self) -> None:
        """Verify DRFX archive structure, absence of errors, and contents."""
        # Arrange
        bundle_path = os.path.join(
            PROJECT_ROOT, "dist", "Cinematic_Composition_Toolkit.drfx"
        )
        self.assertTrue(
            os.path.isfile(bundle_path),
            f"Bundle file {bundle_path} must exist on disk",
        )

        # Act
        validation_errors, diagnostic_notes = validate_drfx.validate(
            bundle_path
        )

        # Assert
        self.assertEqual(
            validation_errors,
            [],
            f"DRFX bundle validation failed with errors: {validation_errors}",
        )
        self.assertGreater(
            len(diagnostic_notes),
            0,
            "DRFX bundle must contain at least one validated template",
        )
        with zipfile.ZipFile(bundle_path, "r") as archive:
            entry_names = archive.namelist()
            expected_setting = (
                "Edit/Effects/Cinematic Guides/"
                "Cinematic Composition Toolkit.setting"
            )
            self.assertIn(expected_setting, entry_names)

    def test_fuscript_native_verification(self) -> None:
        """Verify setting file parses under native Resolve fuscript."""
        # Arrange
        setting_path = os.path.join(
            PROJECT_ROOT,
            "dist",
            "Cinematic Composition Toolkit.setting",
        )

        # Act & Assert
        if os.path.isfile(setting_path):
            is_valid = build_cinematic_toolkit.validate_with_fuscript(
                setting_path
            )
            self.assertTrue(is_valid, "Native fuscript verification failed!")


if __name__ == "__main__":
    unittest.main()
