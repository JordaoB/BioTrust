"""
BioTrust - Liveness Detection Demo
===================================
Demonstrates all liveness detection modes available in BioTrust.

Modes:
1. Active Liveness - User interactions (blink, head movements)
2. Passive Liveness - Heart rate detection via rPPG
3. Multi-Factor - Both active + passive (maximum security)
"""

from payment_system import PaymentSystem
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)


def print_header():
    """Print demo header."""
    print("\n" + "="*70)
    print(Fore.CYAN + Style.BRIGHT + "🔐 BioTrust - Advanced Liveness Detection Demo")
    print("="*70)


def print_mode_info(mode):
    """Print information about the selected mode."""
    info = {
        "active": {
            "name": "Active Liveness Detection",
            "icon": "🎭",
            "desc": "Requires user interaction (blink + head movements)",
            "security": "⭐⭐⭐",
            "speed": "Fast (15-30s)"
        },
        "passive": {
            "name": "Passive Liveness Detection (rPPG)",
            "icon": "🫀",
            "desc": "Detects heart rate through facial color variations",
            "security": "⭐⭐⭐⭐",
            "speed": "Medium (15s)"
        },
        "multi": {
            "name": "Multi-Factor Liveness",
            "icon": "🛡️",
            "desc": "Combines active + passive for maximum security",
            "security": "⭐⭐⭐⭐⭐",
            "speed": "Slower (30-45s)"
        }
    }
    
    data = info.get(mode, {})
    print(f"\n{data.get('icon', '')} {Fore.YELLOW}{data.get('name', 'Unknown')}")
    print(f"Description: {data.get('desc', '')}")
    print(f"Security Level: {data.get('security', '')}")
    print(f"Duration: {data.get('speed', '')}\n")


def demo_active():
    """Demo active liveness only."""
    print_mode_info("active")
    
    ps = PaymentSystem()
    
    # Simulate high-risk transaction
    transaction = {
        "amount": 850.0,
        "location": "madrid",
        "type": "online",
        "timestamp": datetime.now().isoformat()
    }
    
    result = ps.process_payment(
        "joao_regular",
        transaction,
        enable_liveness=True,
        liveness_mode="active"
    )
    
    return result


def demo_passive():
    """Demo passive liveness only."""
    print_mode_info("passive")
    
    ps = PaymentSystem()
    
    # Simulate high-risk transaction
    transaction = {
        "amount": 1200.0,
        "location": "paris",
        "type": "online",
        "timestamp": datetime.now().isoformat()
    }
    
    result = ps.process_payment(
        "joao_regular",
        transaction,
        enable_liveness=True,
        liveness_mode="passive"
    )
    
    return result


def demo_multi():
    """Demo multi-factor liveness."""
    print_mode_info("multi")
    
    print(Fore.YELLOW + "⚠️  MULTI-FACTOR MODE")
    print("This will run BOTH active and passive liveness detection.")
    print("Maximum security but takes longer.\n")
    
    ps = PaymentSystem()
    
    # Simulate very high-risk transaction
    transaction = {
        "amount": 2500.0,
        "location": "paris",
        "type": "online",
        "timestamp": datetime.now().isoformat()
    }
    
    result = ps.process_payment(
        "pedro_suspicious",
        transaction,
        enable_liveness=True,
        liveness_mode="multi"
    )
    
    return result


def standalone_passive_test():
    """Test passive liveness in isolation."""
    print("\n" + "="*70)
    print(Fore.CYAN + "🫀 Standalone Passive Liveness Test")
    print("="*70)
    print("This test runs ONLY the passive (rPPG) heartbeat detection.")
    print("No active liveness required.\n")
    
    from passive_liveness import PassiveLivenessDetector
    
    detector = PassiveLivenessDetector()
    result = detector.verify(show_visualization=True)
    
    print("\n" + "="*70)
    print("RESULT:")
    print(f"  Status: {Fore.GREEN + '✓ LIVE' if result['is_live'] else Fore.RED + '✗ SPOOF'}")
    print(f"  Heart Rate: {result['heart_rate']:.1f} BPM")
    print(f"  Confidence: {result['confidence']:.1%}")
    print("="*70)
    
    return result


def main():
    """Main menu."""
    print_header()
    
    print(Fore.WHITE + "\nChoose a demonstration mode:\n")
    print(f"  {Fore.CYAN}1.{Fore.WHITE} Active Liveness Only")
    print(f"     {Fore.LIGHTBLACK_EX}(Blink + head movements)")
    
    print(f"\n  {Fore.CYAN}2.{Fore.WHITE} Passive Liveness Only (rPPG)")
    print(f"     {Fore.LIGHTBLACK_EX}(Heart rate detection - INNOVATIVE!)")
    
    print(f"\n  {Fore.CYAN}3.{Fore.WHITE} Multi-Factor Liveness")
    print(f"     {Fore.LIGHTBLACK_EX}(Active + Passive - Maximum security)")
    
    print(f"\n  {Fore.CYAN}4.{Fore.WHITE} Standalone Passive Test")
    print(f"     {Fore.LIGHTBLACK_EX}(Test rPPG without payment simulation)")
    
    print(f"\n  {Fore.CYAN}5.{Fore.WHITE} Exit")
    
    choice = input(f"\n{Fore.GREEN}Enter your choice (1-5): ").strip()
    
    if choice == "1":
        print(Fore.GREEN + "\n✓ Starting Active Liveness Demo...")
        demo_active()
    
    elif choice == "2":
        print(Fore.GREEN + "\n✓ Starting Passive Liveness Demo...")
        demo_passive()
    
    elif choice == "3":
        print(Fore.GREEN + "\n✓ Starting Multi-Factor Liveness Demo...")
        demo_multi()
    
    elif choice == "4":
        print(Fore.GREEN + "\n✓ Starting Standalone Passive Test...")
        standalone_passive_test()
    
    elif choice == "5":
        print(Fore.WHITE + "\nThank you for using BioTrust!")
        return
    
    else:
        print(Fore.RED + "\n✗ Invalid choice!")
        return
    
    print(Fore.GREEN + "\n✅ Demo completed!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(Fore.WHITE + "\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(Fore.RED + f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
