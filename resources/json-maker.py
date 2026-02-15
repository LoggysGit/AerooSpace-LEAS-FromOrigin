import json
input = """
Objective: Calculate a deterministic Launch Conditions Score (LCS) based on provided JSON telemetry. Use the mathematical model below.
DEFINES:
 - P_const: 1013.25 hPa (ISO Standard)
 - Cloud_K: Coefficient 0.0 (Clear) to 1.0 (Overcast)
 - Xray_Penalty: C-class = 5, M-class = 30, X-class = 80, else = 0
 - Latitude: Calculation must use RADIANS for trigonometric functions
 - Boolean Logic: true = 1, false = 0
 - Value Constraint: If any Si < 0, then Si = 0
MATHEMATICAL MODEL
  FINAL FORMULA: LCS = (0.35 * S1 + 0.25 * S2 + 0.15 * S3 + 0.15 * S4 + 0.1 * S5) * R1 * R2 * R3
REDLINES (Launch Scrub Gates):
 + R1 (Wind Gate): (max_wind_speed < 30)
 + R2 (Geomagnetic Gate): (kp_index < 7)
 + R3 (Visibility Gate): (visibility > 4000)
INDICES (S1 - S5):
#S1: Atmospheric Stability Index
  Evaluates pressure deviation from ISO standard, optical tracking visibility, and triboelectric charging risks (ice crystal formation at T < -10°C).
  Formula: S1 = [100 - (abs(1013.25 - pressure_surface) / 2)] * 0.4 +
    [min(100, visibility / 100)] * 0.3 +
    [(100 * (1 - cloud_cover)) * (1 - 0.5 * (int(min_wind_temp < -10) + int(average_humidity > 0.7)))] * 0.3
#S2: Aerodynamic Index
  Evaluates wind shear and Max Q (Maximum Dynamic Pressure) stability.
  Formula: S2 = max(0, 33 - max_wind_speed) * 3
#S3: Space Weather Index
  Evaluates avionics protection and communication integrity.
  Formula: S3 = (100 * exp(-0.15 * kp_index)) - Xray_Penalty
#S4: Geoballistic Index
  Evaluates static site advantages (Rotational boost and drag reduction).
  Formula: S4 = 100 * cos(latitude_radians) + (height_msl / 500) - (20 * max(0, slope_degree - 2))
#S5: Operational Safety Index
  Evaluates airspace clearance and terrain suitability.
  Formula: S5 = max(0, 100 - (50 * coef))
  Note: If aircraft_count > 0: coef = aircraft_count. Else: for coef use terrain_type - 0 = "Flat Plain", 0.5 = "Mountainous". If terrain_type = "Sea Level", notice it in your review. Ex: "You must to know, that you will need a floating spaceport, because this point is within sea."
INSTRUCTIONS FOR OUTPUT:
 - Truth and Precision: Do not hallucinate data. If a parameter is missing, state it and set the specific sub-index to 0 AND NOTICE IT in your review. Do not include any conversational filler before or after the JSON
 - LCS Logic: If any R-gate (R1, R2, or R3) is 0, the final LCS MUST be 0.
 - Integration: If "spaceport" is NOT "custom", set S5 to 100 (Safe Operations guaranteed) and ignore slope_degree in S4 (Infrastructure pre-aligned).
 - Strict tresholds: Do not interpret values above the Redline as 'marginal' or 'risky' if they comfortably exceed the limit (e.g., visibility > 10,000m is ideal, not marginal)."
 - Missing data: If any telemetry is null or missing, you MUST set the affected sub-index to 0, flag it in the review and verdict as [MISSING_DATA: PARAMETER_NAME] in ALL CAPS, and explicitly state in the verdict that the final LCS is zeroed due to this specific data gap.
 - !DETERMINISTIC RULE: If R1, R2, and R3 are PASS, you are FORBIDDEN from zeroing the LCS manually. The final score must strictly equal the mathematical result of the S1..S5 and R1..R3 formula.
 - Data priority: Only missing PHYSICAL gates (Wind, Visibility, Pressure, Geomagnetic) result in LCS 0. Missing AQI or minor environmental data should only lower the S-score, not zero out the LCS.
 - JSON Format: You must return a JSON object with the key "ai_analytics" containing:
"ai_analytics": {
  "review": "Detailed technical analysis of the site(s). Cover orbital mechanics, geographical benefits, and atmospheric conditions.",
  "risks": ["Risk 1", "Risk 2", "Risk 3"], // ONLY COLLOCATION/SHORT SENTENCE
  "recommendations": "Specific actionable advice for mission controllers regarding the launch on this point.",
  "verdict": "A concise, high-level executive summary (max 2 sentences).",
  "lcs": 0 // YOU MUST CALCULATE IT ONLY WITH FORMULA, NOT YOURSELF
}
"""
print(json.dumps(input))