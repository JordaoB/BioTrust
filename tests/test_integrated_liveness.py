"""
Quick test for integrated Active + Passive Liveness
"""

from liveness_detector import LivenessDetector

print("🧪 Testing Integrated Active + Passive Liveness Detection\n")
print("This test runs active liveness (blink + head movements)")
print("while simultaneously analyzing your heart rate via rPPG.\n")
print("="*70)

detector = LivenessDetector()
result = detector.verify(timeout_seconds=60, enable_passive=True)

print("\n" + "="*70)
print("FINAL RESULT:")
print(f"  Overall Status: {'✅ APPROVED' if result['success'] else '❌ REJECTED'}")
print(f"  Message: {result['message']}")
print(f"  Blinks Detected: {result['blinks_detected']}")
print(f"  Head Movements: {', '.join(result['head_movements']) if result['head_movements'] else 'None'}")

if 'heart_rate' in result:
    print(f"\n  💓 Heart Rate: {result['heart_rate']:.1f} BPM")
    print(f"  📈 Confidence: {result['heart_rate_confidence']:.1%}")
    print(f"  🫀 Passive Liveness: {'✓ PASS' if result.get('passive_liveness', False) else '✗ FAIL'}")

print("="*70)

if result['success']:
    print("\n✅ Both active and passive liveness confirmed!")
    print("This person is verified as LIVE with heart rate detection.")
else:
    print("\n❌ Liveness verification failed.")
    print("Either active or passive check did not pass.")
