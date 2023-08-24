# Eiger specific
eiger_modules = {"1M": (1, 2), "4M": (2, 4), "9M": (3, 6), "16M": (4, 8)}
eiger_mod_size = (512, 1028)
eiger_gap_size = (38, 12)
intra_mod_gap = 2

# Tristan specific
clock_freq = int(6.4e8)
tristan_modules = {"10M": (2, 5), "2M": (1, 2)}
tristan_mod_size = (515, 2069)  # (H, V)
tristan_gap_size = (117, 45)

# Pre-defined chunk size
tristan_chunk = 2097152

# Junfrau 1M specific
jungfrau_modules = {"1M": (1, 2)}
jungfrau_mod_size = (514, 1030)  # (slow, fast)
jungfrau_gap_size = (38, 12)
jungfrau_fill_value = 0b10000000000000000000000000000000
