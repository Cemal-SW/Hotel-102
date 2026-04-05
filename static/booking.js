document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Flatpickr
    const checkInPicker = flatpickr("#checkIn", {
        minDate: "today",
        dateFormat: "Y-m-d",
        onChange: function(selectedDates, dateStr, instance) {
            checkOutPicker.set('minDate', dateStr);
        }
    });

    const checkOutPicker = flatpickr("#checkOut", {
        minDate: new Date().fp_incr(1),
        dateFormat: "Y-m-d"
    });
});

let state = {
    checkIn: null,
    checkOut: null,
    adults: 2,
    children: 0,
    roomId: null,
    roomName: null,
    roomPrice: 0,
    guestName: '',
    guestEmail: '',
    guestPhone: '',
    specialRequests: '',
    nights: 1
};

function updateSummary() {
    const sumDates = document.getElementById('sum-dates');
    const sumGuests = document.getElementById('sum-guests');
    const sumRoom = document.getElementById('sum-room');
    const sumTotal = document.getElementById('sum-total');

    state.checkIn = document.getElementById('checkIn').value;
    state.checkOut = document.getElementById('checkOut').value;
    state.adults = document.getElementById('adults').value;
    state.children = document.getElementById('children').value;

    if (state.checkIn && state.checkOut) {
        sumDates.innerText = `${state.checkIn} to ${state.checkOut}`;
        const d1 = new Date(state.checkIn);
        const d2 = new Date(state.checkOut);
        state.nights = Math.max(1, (d2 - d1) / (1000 * 60 * 60 * 24));
    }

    sumGuests.innerText = `${state.adults} Adults, ${state.children} Children`;
    sumRoom.innerText = state.roomName || 'Not selected';

    const rawPrice = state.roomPrice.toString().replace(/[^0-9]/g, ''); // Ensure numeric
    const dailyPrice = parseInt(rawPrice) || 0;
    const total = dailyPrice * state.nights;
    
    sumTotal.innerText = `$${total.toLocaleString()}`;
}

function selectRoom(id, name, price) {
    state.roomId = id;
    state.roomName = name;
    state.roomPrice = price;
    
    // Update UI selection
    document.querySelectorAll('.room-card').forEach(el => el.classList.remove('selected'));
    document.querySelectorAll('.room-select-btn').forEach(btn => {
        btn.innerText = "Select";
        btn.classList.remove('bg-primary', 'text-white');
    });

    const card = document.getElementById(`btn-room-${id}`).closest('.room-card');
    card.classList.add('selected');
    
    const btn = document.getElementById(`btn-room-${id}`);
    btn.innerText = "Selected";
    btn.classList.add('bg-primary', 'text-white');

    // Enable next button
    document.getElementById('btn-next-2').disabled = false;
    
    updateSummary();
}

function validateStep(step) {
    if (step === 1) {
        const ci = document.getElementById('checkIn').value;
        const co = document.getElementById('checkOut').value;
        if (!ci || !co) {
            alert('Please select both Check-in and Check-out dates.');
            return false;
        }
    }
    if (step === 2) {
        if (!state.roomId) {
            alert('Please select a room.');
            return false;
        }
    }
    if (step === 3) {
        const name = document.getElementById('guestName').value;
        const email = document.getElementById('guestEmail').value;
        const phone = document.getElementById('guestPhone').value;
        if (!name || !email || !phone) {
            alert('Please fill in all mandatory guest information fields.');
            return false;
        }
        state.guestName = name;
        state.guestEmail = email;
        state.guestPhone = phone;
        state.specialRequests = document.getElementById('specialReq').value;
    }
    if (step === 4) {
        // Mock payment validation
        const ccName = document.getElementById('ccName').value;
        const ccNum = document.getElementById('ccNumber').value;
        if (!ccName || !ccNum) {
            alert('Please enter payment details to secure your reservation.');
            return false;
        }
    }
    return true;
}

function nextStep(stepNum) {
    if (!validateStep(stepNum - 1)) return;
    showStep(stepNum);
    updateSummary();
}

function prevStep(stepNum) {
    showStep(stepNum);
}

function showStep(stepNum) {
    document.querySelectorAll('.step-content').forEach(el => {
        el.classList.remove('active');
    });
    
    // Tiny delay for smooth fade
    setTimeout(() => {
        document.getElementById(`step-${stepNum}`).classList.add('active');
        window.scrollTo({top: 0, behavior: 'smooth'});
    }, 50);

    // Update indicator UI
    for (let i = 1; i <= 4; i++) {
        const ind = document.getElementById(`ind-${i}`);
        if(ind) {
            ind.classList.remove('completed', 'current', 'pending');
            if (i < stepNum) {
                ind.classList.add('completed');
                ind.innerHTML = '<span class="material-symbols-outlined text-xl">check</span>';
            } else if (i === stepNum) {
                ind.classList.add('current');
                ind.innerHTML = i;
            } else {
                ind.classList.add('pending');
                ind.innerHTML = i;
            }
        }
    }
}

async function submitReservation() {
    if (!validateStep(4)) return;

    const btn = document.getElementById('btn-submit');
    btn.disabled = true;
    btn.innerText = "Processing...";

    const payload = {
        checkIn: state.checkIn,
        checkOut: state.checkOut,
        adults: state.adults,
        children: state.children,
        roomId: state.roomId,
        guestName: state.guestName,
        guestEmail: state.guestEmail,
        guestPhone: state.guestPhone,
        specialRequests: state.specialRequests,
        totalPrice: document.getElementById('sum-total').innerText
    };

    try {
        const response = await fetch('/api/reserve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.success) {
            // Show success page
            document.getElementById('res-id').innerText = "#RES-" + String(data.reservation_id).padStart(4, '0');
            showStep(5);
        } else {
            alert('Reservation failed: ' + data.error);
            btn.disabled = false;
            btn.innerText = "Confirm Reservation";
        }
    } catch (e) {
        alert('An error occurred. Please try again.');
        btn.disabled = false;
        btn.innerText = "Confirm Reservation";
    }
}
