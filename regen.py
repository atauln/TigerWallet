import time

from conn import get_formatted_spending, verify_skey_integrity
import database

from threading import Thread

def update_based_on_skey(entry: str, results: list[int], index: int):
    """Update the value based on an skey
    Made for extend_skey()"""

    start = time.perf_counter()
    user = database.get_user_with_skey(entry)
    if user is None:
        return False
    user_settings = database.get_user_settings(user.uid)
    if user_settings is not None:
        if not user_settings.credential_sync:
            return False
    if not verify_skey_integrity(entry):
        database.remove_user(user.uid)
        print (f"Failed to update {user.uid}!")
    else:
        for plan in database.get_meal_plans(user.uid):
            try:
                database.safely_add_purchases(user.uid, get_formatted_spending(database.get_session_data(user.uid), plan.plan_id))
            except Exception:
                pass
        print (f"Updated {user.uid}!")
        results[index] += 1
        print (f"Time taken: {time.perf_counter() - start}")
        return True
    print ("No triggers hit!")
    return False

def extend_skey(minutes, num_threads=8):
    """Extends all skey's in the database"""
    while True:
        skeys = [entry.skey for entry in database.get_all_sessions() if database.get_user_settings(entry.uid).credential_sync]
        starting_length = len(skeys)
        threads = [Thread() for _ in range(num_threads)]
        results = [0 for _ in range(num_threads)]
        while True:
            if len(skeys) > 0:
                for i in range(len(threads)):
                    if not threads[i].is_alive():
                        try:
                            threads[i] = Thread(target=update_based_on_skey, args=(skeys.pop(-1), results, i), name='SkeyUpdate')
                            threads[i].start()
                        except IndexError:
                            break
            if not any([thread.is_alive() for thread in threads]):
                break
            time.sleep(.35)
        print(f"Finished Main Thread! {sum(results)} out of {starting_length} updated!")
        print(f"Results per thread: {results}")
        time.sleep(minutes * 60)
