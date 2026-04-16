const messageEl = document.getElementById('booking-message');
const bookingFlow = document.getElementById('booking-flow');
const BOOKING_DRAFT_STORAGE_KEY = 'hotel102BookingDraftId';
const BOOKING_STATUS_TOKEN_STORAGE_KEY = 'hotel102BookingStatusToken';
const BOOKING_BASE_PATH = document.body?.dataset.bookingBasePath || '';
let calendarInstance = null;
let bookingVersionPollStarted = false;
let currentStep = 1;
let ctaProcessing = false;
const roomAvailabilityState = {
    requestToken: 0,
    loadedKey: '',
    byRoomId: {}
};

const ENHANCEMENT_PRICES = {
    airportTransfer: 85,
    spaTreatment: 150,
    lateCheckout: 50
};

const ENHANCEMENT_LABELS = {
    airportTransfer: 'Airport Transfer',
    spaTreatment: 'Spa Treatment',
    lateCheckout: 'Late Check-out'
};

const bookingState = {
    stay: {
        checkIn: '',
        checkOut: '',
        nights: 1,
        adults: 2,
        children: 0
    },
    room: {
        id: null,
        name: '',
        description: '',
        image: '',
        pricePerNight: 0,
        roomCount: 1,
        totalPrice: 0
    },
    details: {
        primaryGuest: {
            firstName: '',
            lastName: '',
            email: '',
            phone: ''
        },
        adultGuests: [],
        childGuests: [],
        preferences: {
            specialRequests: '',
            arrivalTime: '',
            bedPreference: 'no_preference',
            smokingPreference: 'non_smoking'
        },
        enhancements: {
            airportTransfer: false,
            spaTreatment: false,
            lateCheckout: false
        },
        usePrimaryGuestForAdult1: false
    },
    payment: {
        method: 'card_hold',
        billingName: '',
        billingEmail: '',
        agreedToTerms: false
    },
    meta: {
        bookingDraftId: '',
        statusToken: '',
        approvalStatus: 'PENDING'
    }
};

const state = {
    get checkIn() {
        return bookingState.stay.checkIn;
    },
    set checkIn(value) {
        bookingState.stay.checkIn = value || '';
    },
    get checkOut() {
        return bookingState.stay.checkOut;
    },
    set checkOut(value) {
        bookingState.stay.checkOut = value || '';
    },
    get adults() {
        return bookingState.stay.adults;
    },
    set adults(value) {
        bookingState.stay.adults = Number(value) || 1;
    },
    get children() {
        return bookingState.stay.children;
    },
    set children(value) {
        bookingState.stay.children = Number(value) || 0;
    },
    get nights() {
        return bookingState.stay.nights;
    },
    set nights(value) {
        bookingState.stay.nights = Number(value) || 1;
    },
    get roomId() {
        return bookingState.room.id;
    },
    set roomId(value) {
        bookingState.room.id = value;
    },
    get roomName() {
        return bookingState.room.name;
    },
    set roomName(value) {
        bookingState.room.name = value || '';
    },
    get roomPrice() {
        return bookingState.room.pricePerNight;
    },
    set roomPrice(value) {
        bookingState.room.pricePerNight = value || 0;
    },
    get roomCount() {
        return bookingState.room.roomCount;
    },
    set roomCount(value) {
        bookingState.room.roomCount = Math.max(1, Number(value) || 1);
    },
    get guestEmail() {
        return bookingState.details.primaryGuest.email;
    },
    set guestEmail(value) {
        bookingState.details.primaryGuest.email = value || '';
    },
    get guestPhone() {
        return bookingState.details.primaryGuest.phone;
    },
    set guestPhone(value) {
        bookingState.details.primaryGuest.phone = value || '';
    },
    get specialRequests() {
        return bookingState.details.preferences.specialRequests;
    },
    set specialRequests(value) {
        bookingState.details.preferences.specialRequests = value || '';
    }
};

function setBookingDraftId(value) {
    const bookingDraftId = String(value || '').trim();
    bookingState.meta.bookingDraftId = bookingDraftId;
    if (bookingDraftId) {
        window.sessionStorage.setItem(BOOKING_DRAFT_STORAGE_KEY, bookingDraftId);
    } else {
        window.sessionStorage.removeItem(BOOKING_DRAFT_STORAGE_KEY);
    }
}

function setStatusToken(value) {
    const statusToken = String(value || '').trim();
    bookingState.meta.statusToken = statusToken;
    if (statusToken) {
        window.sessionStorage.setItem(BOOKING_STATUS_TOKEN_STORAGE_KEY, statusToken);
    } else {
        window.sessionStorage.removeItem(BOOKING_STATUS_TOKEN_STORAGE_KEY);
    }
}

function getStoredBookingDraftId() {
    return window.sessionStorage.getItem(BOOKING_DRAFT_STORAGE_KEY) || '';
}

function getStoredStatusToken() {
    return window.sessionStorage.getItem(BOOKING_STATUS_TOKEN_STORAGE_KEY) || '';
}

function getQueryParams() {
    return new URLSearchParams(window.location.search);
}

function buildBookingUrl(path) {
    const normalizedPath = String(path || '').startsWith('/') ? path : `/${path}`;
    return `${BOOKING_BASE_PATH}${normalizedPath}`;
}

function buildBookingDraftPayload() {
    return JSON.parse(JSON.stringify({
        stay: bookingState.stay,
        room: bookingState.room,
        details: bookingState.details,
        payment: bookingState.payment
    }));
}

function toIsoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatDisplayDate(value) {
    if (!value) return '';

    const date = new Date(`${value}T12:00:00`);
    if (Number.isNaN(date.getTime())) return '';

    return new Intl.DateTimeFormat('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(date);
}

function parseManualDateInput(value) {
    const normalized = String(value || '').trim().replace(/\s+/g, '');
    if (!normalized) return null;

    if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
        const parsedIso = new Date(`${normalized}T12:00:00`);
        return Number.isNaN(parsedIso.getTime()) ? null : normalized;
    }

    const match = normalized.match(/^(\d{2})[./-](\d{2})[./-](\d{4})$/);
    if (!match) return null;

    const [, day, month, year] = match;
    const isoValue = `${year}-${month}-${day}`;
    const parsed = new Date(`${isoValue}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return null;
    if (parsed.getDate() !== Number(day) || parsed.getMonth() + 1 !== Number(month) || parsed.getFullYear() !== Number(year)) {
        return null;
    }

    return isoValue;
}

function normalizeDateInputDigits(value) {
    const digits = String(value || '').replace(/\D/g, '').slice(0, 8);
    if (digits.length <= 2) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function setMessage(message, type = 'error') {
    if (!messageEl) return;

    const styles = {
        error: 'border-red-200 bg-red-50 text-red-700',
        success: 'border-green-200 bg-green-50 text-green-700',
        info: 'border-cyan-200 bg-cyan-50 text-cyan-700'
    };

    messageEl.className = `mb-8 rounded-xl border px-4 py-3 text-sm ${styles[type] || styles.info}`;
    messageEl.textContent = message;
    messageEl.classList.remove('hidden');
}

function clearMessage() {
    if (!messageEl) return;
    messageEl.classList.add('hidden');
    messageEl.textContent = '';
}

function scrollToMessage() {
    if (messageEl && !messageEl.classList.contains('hidden')) {
        messageEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else if (bookingFlow) {
        bookingFlow.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function parsePrice(value) {
    const digits = String(value ?? '').replace(/[^0-9]/g, '');
    return parseInt(digits, 10) || 0;
}

function formatCurrency(value) {
    return `$${value.toLocaleString()}`;
}

function readRoomValue(source, keys, fallback = undefined) {
    const target = source?.dataset || source || {};
    for (const key of keys) {
        if (target[key] !== undefined && target[key] !== null && target[key] !== '') {
            return target[key];
        }
    }
    return fallback;
}

function toPositiveInt(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function toBoolean(value, fallback = false) {
    if (typeof value === 'boolean') return value;
    if (value === undefined || value === null || value === '') return fallback;

    const normalized = String(value).trim().toLowerCase();
    if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
    if (['false', '0', 'no', 'off'].includes(normalized)) return false;
    return fallback;
}

function pluralize(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function normalizeRoom(roomSource) {
    const legacyCapacity = Math.max(1, toPositiveInt(readRoomValue(roomSource, ['capacity', 'legacyCapacity']), 2));
    const baseAdults = Math.max(1, toPositiveInt(readRoomValue(roomSource, ['baseAdults', 'base_adults']), legacyCapacity));
    const allowsExtraBed = toBoolean(readRoomValue(roomSource, ['allowsExtraBed', 'allows_extra_bed']), legacyCapacity <= 4);
    const baseChildrenFallback = legacyCapacity <= 2 ? (allowsExtraBed ? 1 : 0) : Math.min(2, legacyCapacity - 2);
    const baseChildren = Math.max(0, toPositiveInt(readRoomValue(roomSource, ['baseChildren', 'base_children']), baseChildrenFallback));
    const maxAdults = Math.max(baseAdults, toPositiveInt(readRoomValue(roomSource, ['maxAdults', 'max_adults']), baseAdults));
    const maxChildren = Math.max(
        baseChildren,
        toPositiveInt(readRoomValue(roomSource, ['maxChildren', 'max_children']), baseChildren + (allowsExtraBed ? 1 : 0))
    );
    const maxOccupancyFallback = Math.min(maxAdults + maxChildren, legacyCapacity + (allowsExtraBed ? 2 : 0));
    const maxOccupancy = Math.max(
        maxAdults,
        baseAdults + baseChildren,
        toPositiveInt(readRoomValue(roomSource, ['maxOccupancy', 'max_occupancy']), maxOccupancyFallback)
    );
    const quantityAvailable = Math.max(0, toPositiveInt(readRoomValue(roomSource, ['quantityAvailable', 'quantity_available']), 1));
    const availableFlag = toBoolean(readRoomValue(roomSource, ['roomAvailable', 'available']), true);
    const available = availableFlag && quantityAvailable > 0;
    const availabilityStatus = String(
        readRoomValue(
            roomSource,
            ['availabilityStatus', 'availability_status'],
            available
                ? (quantityAvailable > 1 ? `${quantityAvailable} rooms available` : 'Available')
                : 'Unavailable for selected dates'
        )
    ).trim();

    return {
        id: Number(readRoomValue(roomSource, ['roomId', 'id'], 0)),
        name: String(readRoomValue(roomSource, ['roomName', 'name'], '')),
        legacyCapacity,
        baseAdults,
        baseChildren,
        maxAdults,
        maxChildren,
        maxOccupancy,
        allowsExtraBed,
        available,
        quantityAvailable,
        availabilityStatus
    };
}

function evaluateSingleRoom(room, adults, children) {
    const normalizedRoom = normalizeRoom(room);
    const adultCount = Math.max(1, Number(adults) || 1);
    const childCount = Math.max(0, Number(children) || 0);
    const totalGuests = adultCount + childCount;
    const baseOccupancy = Math.max(1, normalizedRoom.baseAdults + normalizedRoom.baseChildren);
    const fitsAdults = adultCount <= normalizedRoom.maxAdults;
    const fitsChildren = childCount <= normalizedRoom.maxChildren;
    const fitsTotal = totalGuests <= normalizedRoom.maxOccupancy;
    const singleRoomSuitable = fitsAdults && fitsChildren && fitsTotal;
    const comfortableFit = (
        adultCount <= normalizedRoom.baseAdults
        && childCount <= normalizedRoom.baseChildren
        && totalGuests <= baseOccupancy
    );
    const fitsWithExtraBed = (
        normalizedRoom.allowsExtraBed
        && singleRoomSuitable
        && (
            childCount > normalizedRoom.baseChildren
            || totalGuests > baseOccupancy
        )
    );
    const goodFit = singleRoomSuitable && !comfortableFit && !fitsWithExtraBed;

    return {
        ...normalizedRoom,
        adultCount,
        childCount,
        totalGuests,
        singleRoomSuitable,
        comfortableFit,
        goodFit,
        fitsWithExtraBed,
        fitsAdults,
        fitsChildren,
        fitsTotal
    };
}

function evaluateMultiRoomOption(room, adults, children) {
    const normalizedRoom = normalizeRoom(room);
    const adultCount = Math.max(1, Number(adults) || 1);
    const childCount = Math.max(0, Number(children) || 0);
    const totalGuests = adultCount + childCount;

    if (childCount > 0 && normalizedRoom.maxChildren <= 0) {
        return {
            ...normalizedRoom,
            multiRoomPossible: false,
            requiredRoomCount: 0
        };
    }

    const adultsBased = Math.max(1, normalizedRoom.maxAdults);
    const occupancyBased = Math.max(1, normalizedRoom.maxOccupancy);
    const childrenBased = normalizedRoom.maxChildren;
    const requiredRoomCount = Math.max(
        Math.ceil(adultCount / adultsBased),
        Math.ceil(totalGuests / occupancyBased),
        childCount > 0 ? Math.ceil(childCount / childrenBased) : 1
    );

    return {
        ...normalizedRoom,
        multiRoomPossible: requiredRoomCount > 1,
        requiredRoomCount
    };
}

function evaluateRoomForGuests(room, adults, children) {
    const singleRoom = evaluateSingleRoom(room, adults, children);
    const multiRoom = evaluateMultiRoomOption(room, adults, children);
    const normalizedRoom = singleRoom;

    let selectable = false;
    let recommended = false;
    let score = 0;
    let badge = 'Not suitable';
    let reason = 'Not suitable as a single-room option.';

    if (!normalizedRoom.available) {
        score = -1;
        badge = 'Unavailable';
        reason = normalizedRoom.availabilityStatus || 'Unavailable for selected dates';
    } else if (singleRoom.comfortableFit) {
        selectable = true;
        recommended = true;
        score = 100;
        badge = 'Recommended';
        reason = 'Fits your group comfortably';
    } else if (singleRoom.goodFit) {
        selectable = true;
        score = 85;
        badge = 'Good fit';
        reason = 'Good option for your selected guests';
    } else if (singleRoom.fitsWithExtraBed) {
        selectable = true;
        score = 70;
        badge = 'Fits with extra bed';
        reason = 'Fits with extra bed';
    } else if (multiRoom.multiRoomPossible && multiRoom.requiredRoomCount <= normalizedRoom.quantityAvailable) {
        selectable = true;
        score = 75 - multiRoom.requiredRoomCount;
        badge = 'Multi-room option';
        reason = `${multiRoom.requiredRoomCount} rooms needed for your group`;
    } else if (multiRoom.multiRoomPossible) {
        score = 20;
        badge = 'Limited availability';
        reason = `${multiRoom.requiredRoomCount} rooms required, only ${normalizedRoom.quantityAvailable} available`;
    }

    return {
        ...normalizedRoom,
        singleRoomSuitable: singleRoom.singleRoomSuitable,
        multiRoomPossible: multiRoom.multiRoomPossible,
        requiredRoomCount: singleRoom.singleRoomSuitable ? 1 : multiRoom.requiredRoomCount,
        selectable,
        recommended,
        score,
        badge,
        reason,
        availabilityStatus: normalizedRoom.availabilityStatus,
        fitsAdults: singleRoom.fitsAdults,
        fitsChildren: singleRoom.fitsChildren,
        fitsTotal: singleRoom.fitsTotal,
        fitsWithExtraBed: singleRoom.fitsWithExtraBed,
        comfortableFit: singleRoom.comfortableFit,
        goodFit: singleRoom.goodFit
    };
}

function getRankingBucket(evaluation) {
    if (!evaluation.selectable) return 2;
    if (evaluation.recommended) return 0;
    return 1;
}

function rankRoomOptions(rooms, adults, children) {
    return rooms
        .map((room) => ({
            room,
            evaluation: evaluateRoomForGuests(room, adults, children)
        }))
        .sort((a, b) => {
            if (a.evaluation.score !== b.evaluation.score) return b.evaluation.score - a.evaluation.score;
            const bucketDiff = getRankingBucket(a.evaluation) - getRankingBucket(b.evaluation);
            if (bucketDiff !== 0) return bucketDiff;
            return a.evaluation.id - b.evaluation.id;
        });
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function isValidDateRange(checkIn, checkOut) {
    if (!checkIn || !checkOut) return false;
    const d1 = new Date(`${checkIn}T12:00:00`);
    const d2 = new Date(`${checkOut}T12:00:00`);
    return !Number.isNaN(d1.getTime()) && !Number.isNaN(d2.getTime()) && d2 > d1;
}

function getTotalGuests() {
    return Number(state.adults || 0) + Number(state.children || 0);
}

function getPrimaryGuestFullName() {
    return `${bookingState.details.primaryGuest.firstName} ${bookingState.details.primaryGuest.lastName}`.trim();
}

function getSelectedRoomLabel() {
    if (!bookingState.room.name) return 'Not selected';
    return state.roomCount > 1 ? `${bookingState.room.name} x${state.roomCount}` : bookingState.room.name;
}

function getRoomSubtotal() {
    return parsePrice(bookingState.room.pricePerNight) * Number(bookingState.stay.nights || 1) * Number(state.roomCount || 1);
}

function getSelectedEnhancements() {
    return Object.entries(bookingState.details.enhancements)
        .filter(([, selected]) => Boolean(selected))
        .map(([key]) => ({
            key,
            label: ENHANCEMENT_LABELS[key],
            price: ENHANCEMENT_PRICES[key]
        }));
}

function getEnhancementTotal() {
    return getSelectedEnhancements().reduce((total, item) => total + item.price, 0);
}

function getGrandTotal() {
    return getRoomSubtotal() + getEnhancementTotal();
}

function createAdultGuest() {
    return {
        firstName: '',
        lastName: '',
        nationality: '',
        passportOrId: ''
    };
}

function createChildGuest() {
    return {
        firstName: '',
        lastName: '',
        age: ''
    };
}

function ensureGuestStateShape() {
    const adultCount = Math.max(1, Number(bookingState.stay.adults || 1));
    const childCount = Math.max(0, Number(bookingState.stay.children || 0));
    const adultChanged = bookingState.details.adultGuests.length !== adultCount;
    const childChanged = bookingState.details.childGuests.length !== childCount;

    if (adultChanged) {
        bookingState.details.adultGuests = Array.from({ length: adultCount }, (_, index) => (
            bookingState.details.adultGuests[index] || createAdultGuest()
        ));
    }

    if (childChanged) {
        bookingState.details.childGuests = Array.from({ length: childCount }, (_, index) => (
            bookingState.details.childGuests[index] || createChildGuest()
        ));
    }

    if (bookingState.details.usePrimaryGuestForAdult1 && bookingState.details.adultGuests[0]) {
        syncPrimaryGuestToAdultOne();
    }

    return adultChanged || childChanged;
}

function syncPrimaryGuestToAdultOne() {
    if (!bookingState.details.adultGuests[0]) return;

    bookingState.details.adultGuests[0] = {
        ...bookingState.details.adultGuests[0],
        firstName: bookingState.details.primaryGuest.firstName,
        lastName: bookingState.details.primaryGuest.lastName
    };
}

function renderAdultGuestFields() {
    const container = document.getElementById('adultGuestsContainer');
    if (!container) return;

    container.innerHTML = bookingState.details.adultGuests.map((guest, index) => `
        <article class="details-dynamic-card">
            <div class="details-dynamic-header">
                <h5>Adult ${index + 1}</h5>
                <span>${index === 0 ? 'Lead occupancy' : 'Guest profile'}</span>
            </div>
            <div class="details-field-grid">
                <div class="details-field">
                    <label class="details-label" for="adult-${index}-firstName">First Name <span class="text-error">*</span></label>
                    <input type="text" id="adult-${index}-firstName" class="input-field" data-field-key="details.adultGuests.${index}.firstName" value="${escapeHtml(guest.firstName)}" placeholder="First name">
                    <p class="field-error hidden" data-field-error="details.adultGuests.${index}.firstName"></p>
                </div>
                <div class="details-field">
                    <label class="details-label" for="adult-${index}-lastName">Last Name <span class="text-error">*</span></label>
                    <input type="text" id="adult-${index}-lastName" class="input-field" data-field-key="details.adultGuests.${index}.lastName" value="${escapeHtml(guest.lastName)}" placeholder="Last name">
                    <p class="field-error hidden" data-field-error="details.adultGuests.${index}.lastName"></p>
                </div>
                <div class="details-field">
                    <label class="details-label" for="adult-${index}-nationality">Nationality</label>
                    <input type="text" id="adult-${index}-nationality" class="input-field" data-field-key="details.adultGuests.${index}.nationality" value="${escapeHtml(guest.nationality)}" placeholder="Optional">
                    <p class="field-error hidden" data-field-error="details.adultGuests.${index}.nationality"></p>
                </div>
                <div class="details-field">
                    <label class="details-label" for="adult-${index}-passport">ID / Passport Number <span class="text-error">*</span></label>
                    <input type="text" id="adult-${index}-passport" class="input-field" data-field-key="details.adultGuests.${index}.passportOrId" value="${escapeHtml(guest.passportOrId)}" placeholder="Passport or ID number" required>
                    <p class="field-error hidden" data-field-error="details.adultGuests.${index}.passportOrId"></p>
                </div>
            </div>
        </article>
    `).join('');
}

function renderChildGuestFields() {
    const section = document.getElementById('childGuestsSection');
    const container = document.getElementById('childGuestsContainer');
    if (!section || !container) return;

    if (!bookingState.details.childGuests.length) {
        section.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    section.classList.remove('hidden');
    container.innerHTML = bookingState.details.childGuests.map((guest, index) => `
        <article class="details-dynamic-card">
            <div class="details-dynamic-header">
                <h5>Child ${index + 1}</h5>
                <span>Guest profile</span>
            </div>
            <div class="details-field-grid">
                <div class="details-field">
                    <label class="details-label" for="child-${index}-firstName">First Name <span class="text-error">*</span></label>
                    <input type="text" id="child-${index}-firstName" class="input-field" data-field-key="details.childGuests.${index}.firstName" value="${escapeHtml(guest.firstName)}" placeholder="First name">
                    <p class="field-error hidden" data-field-error="details.childGuests.${index}.firstName"></p>
                </div>
                <div class="details-field">
                    <label class="details-label" for="child-${index}-lastName">Last Name <span class="text-error">*</span></label>
                    <input type="text" id="child-${index}-lastName" class="input-field" data-field-key="details.childGuests.${index}.lastName" value="${escapeHtml(guest.lastName)}" placeholder="Last name">
                    <p class="field-error hidden" data-field-error="details.childGuests.${index}.lastName"></p>
                </div>
                <div class="details-field details-field-wide">
                    <label class="details-label" for="child-${index}-age">Age <span class="text-error">*</span></label>
                    <input type="number" id="child-${index}-age" class="input-field" data-field-key="details.childGuests.${index}.age" value="${escapeHtml(guest.age)}" min="0" max="17" placeholder="Age">
                    <p class="field-error hidden" data-field-error="details.childGuests.${index}.age"></p>
                </div>
            </div>
        </article>
    `).join('');
}

function renderGuestSections() {
    ensureGuestStateShape();
    renderAdultGuestFields();
    renderChildGuestFields();

    const usePrimaryCheckbox = document.getElementById('usePrimaryForAdult1');
    if (usePrimaryCheckbox) {
        usePrimaryCheckbox.checked = Boolean(bookingState.details.usePrimaryGuestForAdult1);
    }
}

function hydrateDetailsForm() {
    const fieldMap = {
        primaryFirstName: bookingState.details.primaryGuest.firstName,
        primaryLastName: bookingState.details.primaryGuest.lastName,
        primaryEmail: bookingState.details.primaryGuest.email,
        primaryPhone: bookingState.details.primaryGuest.phone,
        specialReq: bookingState.details.preferences.specialRequests,
        arrivalTime: bookingState.details.preferences.arrivalTime,
        bedPreference: bookingState.details.preferences.bedPreference,
        smokingPreference: bookingState.details.preferences.smokingPreference
    };

    Object.entries(fieldMap).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = Boolean(value);
            } else {
                element.value = value || '';
            }
        }
    });

    renderGuestSections();
    updateEnhancementSelectionUI();
}

function hydratePaymentForm() {
    if (!bookingState.payment.billingName) {
        bookingState.payment.billingName = getPrimaryGuestFullName();
    }

    if (!bookingState.payment.billingEmail) {
        bookingState.payment.billingEmail = bookingState.details.primaryGuest.email;
    }

    const billingName = document.getElementById('billingName');
    const billingEmail = document.getElementById('billingEmail');
    const paymentTerms = document.getElementById('paymentTerms');

    if (billingName) billingName.value = bookingState.payment.billingName || '';
    if (billingEmail) billingEmail.value = bookingState.payment.billingEmail || '';
    if (paymentTerms) paymentTerms.checked = Boolean(bookingState.payment.agreedToTerms);

    document.querySelectorAll('input[name="paymentMethod"]').forEach((input) => {
        input.checked = input.value === bookingState.payment.method;
    });
    updatePaymentMethodUI();

    const ccName = document.getElementById('ccName');
    if (ccName && !ccName.value && bookingState.payment.billingName) {
        ccName.value = bookingState.payment.billingName.toUpperCase();
    }
}

function setNestedValue(target, path, value) {
    const keys = path.split('.');
    let current = target;

    for (let index = 0; index < keys.length - 1; index += 1) {
        const key = /^\d+$/.test(keys[index]) ? Number(keys[index]) : keys[index];
        current = current[key];
    }

    const lastKey = /^\d+$/.test(keys[keys.length - 1]) ? Number(keys[keys.length - 1]) : keys[keys.length - 1];
    current[lastKey] = value;
}

function syncFieldIntoBookingState(field) {
    const path = field?.dataset?.fieldKey;
    if (!path) return;

    let value;
    if (field.type === 'checkbox') {
        value = field.checked;
    } else if (field.type === 'number') {
        value = field.value === '' ? '' : Number(field.value);
    } else {
        value = field.value;
    }

    setNestedValue(bookingState, path, value);
}

function clearFieldError(fieldKey) {
    const field = document.querySelector(`[data-field-key="${fieldKey}"]`);
    const error = document.querySelector(`[data-field-error="${fieldKey}"]`);

    if (field) {
        field.classList.remove('is-invalid');
        field.removeAttribute('aria-invalid');
    }

    if (error) {
        error.textContent = '';
        error.classList.add('hidden');
    }
}

function clearValidationErrors() {
    document.querySelectorAll('[data-field-key]').forEach((field) => {
        field.classList.remove('is-invalid');
        field.removeAttribute('aria-invalid');
    });

    document.querySelectorAll('[data-field-error]').forEach((error) => {
        error.textContent = '';
        error.classList.add('hidden');
    });
}

function setFieldError(fieldKey, message) {
    const field = document.querySelector(`[data-field-key="${fieldKey}"]`);
    const error = document.querySelector(`[data-field-error="${fieldKey}"]`);

    if (field) {
        field.classList.add('is-invalid');
        field.setAttribute('aria-invalid', 'true');
    }

    if (error) {
        error.textContent = message;
        error.classList.remove('hidden');
    }
}

function scrollToFirstInvalidField() {
    const firstInvalidField = document.querySelector('.is-invalid');
    if (firstInvalidField) {
        firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        firstInvalidField.focus({ preventScroll: true });
    } else {
        scrollToMessage();
    }
}

function updateEnhancementSelectionUI() {
    document.querySelectorAll('[data-enhancement-key]').forEach((button) => {
        const key = button.dataset.enhancementKey;
        const isSelected = Boolean(bookingState.details.enhancements[key]);
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
    });
}

function updatePaymentMethodUI() {
    document.querySelectorAll('.payment-method-card').forEach((card) => {
        const input = card.querySelector('input[name="paymentMethod"]');
        card.classList.toggle('selected', Boolean(input?.checked));
    });
}

function syncDetailsStepState() {
    document.querySelectorAll('#step-3 [data-field-key]').forEach((field) => {
        syncFieldIntoBookingState(field);
    });

    const usePrimaryCheckbox = document.getElementById('usePrimaryForAdult1');
    bookingState.details.usePrimaryGuestForAdult1 = Boolean(usePrimaryCheckbox?.checked);
    if (bookingState.details.usePrimaryGuestForAdult1) {
        syncPrimaryGuestToAdultOne();
    }
}

function syncPaymentStepState() {
    document.querySelectorAll('#step-4 [data-field-key]').forEach((field) => {
        syncFieldIntoBookingState(field);
    });

    const selectedMethod = document.querySelector('input[name="paymentMethod"]:checked');
    if (selectedMethod) {
        bookingState.payment.method = selectedMethod.value;
    }
}

function validateEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validatePhone(value) {
    return String(value || '').replace(/\D/g, '').length >= 7;
}

function getDetailsValidationErrors() {
    const errors = [];
    const primaryGuest = bookingState.details.primaryGuest;

    if (!primaryGuest.firstName.trim()) {
        errors.push(['details.primaryGuest.firstName', 'Primary guest first name is required.']);
    }
    if (!primaryGuest.lastName.trim()) {
        errors.push(['details.primaryGuest.lastName', 'Primary guest last name is required.']);
    }
    if (!primaryGuest.email.trim()) {
        errors.push(['details.primaryGuest.email', 'Primary guest email is required.']);
    } else if (!validateEmail(primaryGuest.email)) {
        errors.push(['details.primaryGuest.email', 'Please enter a valid email address.']);
    }
    if (!primaryGuest.phone.trim()) {
        errors.push(['details.primaryGuest.phone', 'Primary guest phone number is required.']);
    } else if (!validatePhone(primaryGuest.phone)) {
        errors.push(['details.primaryGuest.phone', 'Please enter a valid phone number.']);
    }

    bookingState.details.adultGuests.forEach((guest, index) => {
        if (!guest.firstName.trim()) {
            errors.push([`details.adultGuests.${index}.firstName`, `Adult ${index + 1} first name is required.`]);
        }
        if (!guest.lastName.trim()) {
            errors.push([`details.adultGuests.${index}.lastName`, `Adult ${index + 1} last name is required.`]);
        }
        if (!String(guest.passportOrId || '').trim()) {
            errors.push([`details.adultGuests.${index}.passportOrId`, `Adult ${index + 1} ID / passport number is required.`]);
        }
    });

    bookingState.details.childGuests.forEach((guest, index) => {
        if (!guest.firstName.trim()) {
            errors.push([`details.childGuests.${index}.firstName`, `Child ${index + 1} first name is required.`]);
        }
        if (!guest.lastName.trim()) {
            errors.push([`details.childGuests.${index}.lastName`, `Child ${index + 1} last name is required.`]);
        }
        if (guest.age === '' || Number.isNaN(Number(guest.age)) || Number(guest.age) < 0) {
            errors.push([`details.childGuests.${index}.age`, `Child ${index + 1} age is required.`]);
        }
    });

    return errors;
}

function validateDetailsStep() {
    syncDetailsStepState();
    clearValidationErrors();
    const errors = getDetailsValidationErrors();

    if (errors.length) {
        errors.forEach(([fieldKey, message]) => setFieldError(fieldKey, message));
        setMessage('Please complete the required guest details before continuing.');
        scrollToFirstInvalidField();
        return false;
    }

    return true;
}

function getPaymentValidationErrors() {
    const errors = [];

    if (!bookingState.payment.method) {
        errors.push(['payment.method', 'Please choose a payment method.']);
    } else if (bookingState.payment.method !== 'card_hold') {
        errors.push(['payment.method', 'Sandbox iyzico Checkout Form is the only supported payment path right now.']);
    }

    if (!bookingState.payment.billingName.trim()) {
        errors.push(['payment.billingName', 'Billing name is required.']);
    }

    if (!bookingState.payment.billingEmail.trim()) {
        errors.push(['payment.billingEmail', 'Billing email is required.']);
    } else if (!validateEmail(bookingState.payment.billingEmail)) {
        errors.push(['payment.billingEmail', 'Please enter a valid billing email address.']);
    }

    if (!bookingState.payment.agreedToTerms) {
        errors.push(['payment.agreedToTerms', 'You must agree to the booking terms before confirming.']);
    }

    return errors;
}

function validatePaymentStep() {
    syncPaymentStepState();
    clearValidationErrors();
    const errors = getPaymentValidationErrors();

    if (errors.length) {
        errors.forEach(([fieldKey, message]) => setFieldError(fieldKey, message));
        setMessage('Please complete the payment confirmation fields before submitting.');
        scrollToFirstInvalidField();
        return false;
    }

    return true;
}

function updatePaymentSummary() {
    const sumDates = document.getElementById('sum-dates');
    const sumGuests = document.getElementById('sum-guests');
    const sumRoom = document.getElementById('sum-room');
    const sumRoomTotal = document.getElementById('sum-room-total');
    const sumEnhancements = document.getElementById('sum-enhancements');
    const sumTotal = document.getElementById('sum-total');
    const paymentPrimaryGuest = document.getElementById('payment-primary-guest');
    const enhancementList = document.getElementById('payment-enhancement-list');

    if (sumDates) {
        sumDates.innerText = isValidDateRange(state.checkIn, state.checkOut)
            ? `${formatDisplayDate(state.checkIn)} - ${formatDisplayDate(state.checkOut)}`
            : 'Select dates';
    }

    if (sumGuests) {
        sumGuests.innerText = `${state.adults} Adults, ${state.children} Children`;
    }

    if (sumRoom) {
        sumRoom.innerText = getSelectedRoomLabel();
    }

    if (sumRoomTotal) {
        sumRoomTotal.innerText = formatCurrency(getRoomSubtotal());
    }

    if (sumEnhancements) {
        sumEnhancements.innerText = formatCurrency(getEnhancementTotal());
    }

    if (sumTotal) {
        sumTotal.innerText = formatCurrency(getGrandTotal());
    }

    if (paymentPrimaryGuest) {
        paymentPrimaryGuest.innerText = getPrimaryGuestFullName() || 'To be provided';
    }

    if (enhancementList) {
        const enhancements = getSelectedEnhancements();
        enhancementList.innerText = enhancements.length
            ? enhancements.map((item) => `${item.label} (${formatCurrency(item.price)})`).join(' · ')
            : 'No enhancements selected.';
    }
}

function isStayStepReady() {
    return bookingFlow?.dataset.hasRooms === 'true'
        && Boolean(state.checkIn)
        && Boolean(state.checkOut)
        && isValidDateRange(state.checkIn, state.checkOut);
}

function isRoomStepReady() {
    return Boolean(state.roomId) && canSelectedRoomFitGuests();
}

function isDetailsStepReady() {
    syncDetailsStepState();
    return getDetailsValidationErrors().length === 0;
}

function isPaymentStepReady() {
    syncPaymentStepState();
    return getPaymentValidationErrors().length === 0;
}

function getStickyCtaConfig(stepNum) {
    const selectedEnhancements = getSelectedEnhancements();

    if (stepNum === 1) {
        return {
            visible: false,
            eyebrow: 'Stay',
            summary: isStayStepReady()
                ? `${formatDisplayDate(state.checkIn)} - ${formatDisplayDate(state.checkOut)} · ${state.adults} Adults, ${state.children} Children`
                : 'Select dates and guests to continue.',
            priceLabel: 'Current Total',
            total: formatCurrency(getRoomSubtotal()),
            buttonText: 'Continue',
            disabled: !isStayStepReady()
        };
    }

    if (stepNum === 2) {
        return {
            visible: true,
            eyebrow: 'Room',
            summary: bookingState.room.name
                ? `${getSelectedRoomLabel()} selected`
                : 'Select a room to continue.',
            priceLabel: 'Room Total',
            total: formatCurrency(getRoomSubtotal()),
            buttonText: 'Continue with Selected Room',
            disabled: !isRoomStepReady()
        };
    }

    if (stepNum === 3) {
        return {
            visible: true,
            eyebrow: 'Details',
            summary: selectedEnhancements.length
                ? `${selectedEnhancements.length} enhancement${selectedEnhancements.length === 1 ? '' : 's'} selected`
                : 'Complete guest details to continue to payment.',
            priceLabel: 'Grand Total',
            total: formatCurrency(getGrandTotal()),
            buttonText: 'Continue to Payment',
            disabled: !isDetailsStepReady()
        };
    }

    if (stepNum === 4) {
        return {
            visible: true,
            eyebrow: 'Payment',
            summary: getPrimaryGuestFullName() || 'Review payment details and confirm your reservation.',
            priceLabel: 'Grand Total',
            total: formatCurrency(getGrandTotal()),
            buttonText: ctaProcessing ? 'Redirecting...' : 'Continue to Secure Payment',
            disabled: ctaProcessing || !isPaymentStepReady()
        };
    }

    return {
        visible: false,
        eyebrow: '',
        summary: '',
        priceLabel: 'Grand Total',
        total: formatCurrency(getGrandTotal()),
        buttonText: 'Continue',
        disabled: true
    };
}

function updateStickyBookingCta() {
    const cta = document.getElementById('sticky-booking-cta');
    const label = document.getElementById('sticky-cta-label');
    const summary = document.getElementById('sticky-cta-summary');
    const total = document.getElementById('sticky-cta-total');
    const button = document.getElementById('sticky-cta-button');
    const priceLabel = cta?.querySelector('.booking-sticky-cta-price-label');

    if (!cta || !label || !summary || !total || !button || !priceLabel) return;

    const config = getStickyCtaConfig(currentStep);
    cta.classList.toggle('is-visible', config.visible);
    cta.classList.toggle('is-hidden', !config.visible);
    cta.dataset.step = String(currentStep);

    label.textContent = config.eyebrow;
    summary.textContent = config.summary;
    priceLabel.textContent = config.priceLabel;
    total.textContent = config.total;
    button.textContent = config.buttonText;
    button.disabled = config.disabled;
    button.setAttribute('aria-disabled', config.disabled ? 'true' : 'false');
}

function handleStickyCtaClick() {
    if (currentStep === 1) {
        nextStep(2);
        return;
    }

    if (currentStep === 2) {
        nextStep(3);
        return;
    }

    if (currentStep === 3) {
        nextStep(4);
        return;
    }

    if (currentStep === 4) {
        submitReservation();
    }
}

function prepareStep(stepNum) {
    if (stepNum === 3) {
        hydrateDetailsForm();
    }

    if (stepNum === 4) {
        hydratePaymentForm();
    }
}

function buildReservationSpecialRequests() {
    const preferences = bookingState.details.preferences;
    const parts = [];

    if (preferences.specialRequests) {
        parts.push(`Special requests: ${preferences.specialRequests}`);
    }
    if (preferences.arrivalTime) {
        parts.push(`Arrival time: ${preferences.arrivalTime}`);
    }
    if (preferences.bedPreference && preferences.bedPreference !== 'no_preference') {
        parts.push(`Bed preference: ${preferences.bedPreference}`);
    }
    if (preferences.smokingPreference && preferences.smokingPreference !== 'no_preference') {
        parts.push(`Smoking preference: ${preferences.smokingPreference}`);
    }

    const enhancements = getSelectedEnhancements();
    if (enhancements.length) {
        parts.push(`Enhancements: ${enhancements.map((item) => item.label).join(', ')}`);
    }

    return parts.join(' | ');
}

function updateMonthLabel(instance) {
    const monthElement = document.getElementById('custom-month-name');
    if (!monthElement || !instance) return;

    const monthName = instance.l10n.months.longhand[instance.currentMonth];
    monthElement.innerText = `${monthName} ${instance.currentYear}`;
}

function syncStayDisplay() {
    const checkInDisplay = document.getElementById('checkInDisplay');
    const checkOutDisplay = document.getElementById('checkOutDisplay');
    const stayNights = document.getElementById('stay-nights');

    if (checkInDisplay && document.activeElement !== checkInDisplay) {
        checkInDisplay.value = formatDisplayDate(state.checkIn);
    }

    if (checkOutDisplay && document.activeElement !== checkOutDisplay) {
        checkOutDisplay.value = formatDisplayDate(state.checkOut);
    }

    if (stayNights) {
        if (isValidDateRange(state.checkIn, state.checkOut)) {
            stayNights.textContent = `${state.nights} night${state.nights === 1 ? '' : 's'} selected`;
        } else {
            stayNights.textContent = 'Choose your stay dates';
        }
    }
}

function updateDetailsSummary() {
    const detailsStay = document.getElementById('details-stay');
    const detailsGuests = document.getElementById('details-guests');
    const detailsRoom = document.getElementById('details-room');
    const detailsPrimaryGuest = document.getElementById('details-primary-guest');
    const detailsEnhancementList = document.getElementById('details-enhancement-list');
    const detailsEnhancementTotal = document.getElementById('details-enhancements-total');
    const detailsGrandTotal = document.getElementById('details-grand-total');

    if (detailsStay) {
        detailsStay.textContent = isValidDateRange(state.checkIn, state.checkOut)
            ? `${formatDisplayDate(state.checkIn)} - ${formatDisplayDate(state.checkOut)}`
            : 'Select dates';
    }

    if (detailsGuests) {
        detailsGuests.textContent = `${state.adults} Adults, ${state.children} Children`;
    }

    if (detailsRoom) {
        detailsRoom.textContent = getSelectedRoomLabel();
    }

    if (detailsPrimaryGuest) {
        detailsPrimaryGuest.textContent = getPrimaryGuestFullName() || 'To be provided';
    }

    if (detailsEnhancementList) {
        const enhancements = getSelectedEnhancements();
        detailsEnhancementList.textContent = enhancements.length
            ? enhancements.map((item) => item.label).join(', ')
            : 'None selected';
    }

    if (detailsEnhancementTotal) {
        detailsEnhancementTotal.textContent = formatCurrency(getEnhancementTotal());
    }

    if (detailsGrandTotal) {
        detailsGrandTotal.textContent = formatCurrency(getGrandTotal());
    }
}

function resetSelectedRoomState() {
    state.roomId = null;
    state.roomName = '';
    state.roomPrice = 0;
    state.roomCount = 1;
    bookingState.room.description = '';
    bookingState.room.image = '';
    bookingState.room.totalPrice = getRoomSubtotal();
    document.querySelectorAll('.room-card').forEach((card) => {
        card.classList.remove('selected');
        card.setAttribute('aria-pressed', 'false');
    });

    document.querySelectorAll('.room-select-btn.is-selected').forEach((button) => {
        button.textContent = 'Select room';
        button.classList.remove('is-selected');
    });

    const roomStepSelected = document.getElementById('room-step-selected');
    const roomStepTotal = document.getElementById('room-step-total');
    if (roomStepSelected) roomStepSelected.textContent = 'Choose a room';
    if (roomStepTotal) roomStepTotal.textContent = formatCurrency(getRoomSubtotal());

    updateDetailsSummary();
    updatePaymentSummary();
}

function applyRoomAvailabilitySnapshot(snapshot) {
    const roomList = document.getElementById('roomList');
    if (!roomList) return;

    Object.values(snapshot || {}).forEach((room) => {
        const card = roomList.querySelector(`[data-room-id="${room.roomId}"]`);
        if (!card) return;

        card.dataset.roomAvailable = room.available ? 'true' : 'false';
        card.dataset.quantityAvailable = String(room.quantityAvailable ?? 0);
        card.dataset.availabilityStatus = room.availabilityStatus || '';
    });
}

async function syncRoomAvailabilityForStay() {
    if (!isValidDateRange(state.checkIn, state.checkOut)) return;

    const requestKey = `${state.checkIn}|${state.checkOut}`;
    if (roomAvailabilityState.loadedKey === requestKey) return;

    const token = roomAvailabilityState.requestToken + 1;
    roomAvailabilityState.requestToken = token;

    try {
        const response = await fetch(`${buildBookingUrl('/api/room-availability')}?checkIn=${encodeURIComponent(state.checkIn)}&checkOut=${encodeURIComponent(state.checkOut)}`, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        if (!response.ok) return;

        const data = await response.json();
        if (!data?.success || token !== roomAvailabilityState.requestToken) return;

        roomAvailabilityState.byRoomId = Object.fromEntries(
            (data.rooms || []).map((room) => [String(room.roomId), room])
        );
        roomAvailabilityState.loadedKey = requestKey;
        applyRoomAvailabilitySnapshot(roomAvailabilityState.byRoomId);
        updateRoomRecommendations();
        updateStickyBookingCta();
    } catch (_error) {
        // Ignore transient availability sync failures.
    }
}

function applyRoomEvaluationToCard(card, evaluation) {
    const badge = document.getElementById(`room-badge-${card.dataset.roomId}`);
    const status = document.getElementById(`room-status-${card.dataset.roomId}`);
    const reason = document.getElementById(`room-reason-${card.dataset.roomId}`);
    const button = document.getElementById(`btn-room-${card.dataset.roomId}`);
    const disabled = !evaluation.selectable;

    card.dataset.selectable = evaluation.selectable ? 'true' : 'false';
    card.dataset.recommended = evaluation.recommended ? 'true' : 'false';
    card.dataset.score = String(evaluation.score);
    card.dataset.badge = evaluation.badge;
    card.dataset.reason = evaluation.reason;
    card.dataset.availabilityStatus = evaluation.availabilityStatus;
    card.dataset.fitsAdults = evaluation.fitsAdults ? 'true' : 'false';
    card.dataset.fitsChildren = evaluation.fitsChildren ? 'true' : 'false';
    card.dataset.fitsTotal = evaluation.fitsTotal ? 'true' : 'false';
    card.dataset.singleRoomSuitable = evaluation.singleRoomSuitable ? 'true' : 'false';
    card.dataset.multiRoomPossible = evaluation.multiRoomPossible ? 'true' : 'false';
    card.dataset.requiredRoomCount = String(evaluation.requiredRoomCount || 0);
    card.dataset.fitsWithExtraBed = evaluation.fitsWithExtraBed ? 'true' : 'false';

    card.classList.toggle('recommended-room', evaluation.recommended);
    card.classList.toggle('room-unavailable', disabled);
    card.setAttribute('aria-disabled', disabled ? 'true' : 'false');
    card.tabIndex = disabled ? -1 : 0;

    if (badge) {
        badge.textContent = evaluation.badge;
        badge.dataset.badgeTone = evaluation.recommended ? 'highlight' : 'muted';
        badge.classList.remove('hidden');
    }

    if (status) {
        status.textContent = evaluation.availabilityStatus;
    }

    if (reason) {
        reason.textContent = evaluation.reason;
    }

    if (button) {
        button.disabled = disabled;
        button.setAttribute('aria-disabled', disabled ? 'true' : 'false');
        button.textContent = disabled
            ? (evaluation.score === 20 ? 'Limited' : (evaluation.available ? 'Not suitable' : 'Unavailable'))
            : (evaluation.requiredRoomCount > 1 ? `Select ${evaluation.requiredRoomCount} rooms` : 'Select room');
        button.classList.remove('is-selected');
    }
}

function updateRoomRecommendations() {
    const roomList = document.getElementById('roomList');
    const recommendationNote = document.getElementById('room-recommendation-note');

    if (!roomList) return;

    const cards = Array.from(roomList.querySelectorAll('[data-room-card]'));
    const rankedRooms = rankRoomOptions(cards, state.adults, state.children);
    let recommendedCount = 0;
    let alternativeCount = 0;
    let disabledCount = 0;

    rankedRooms.forEach(({ room, evaluation }) => {
        applyRoomEvaluationToCard(room, evaluation);
        if (evaluation.recommended) {
            recommendedCount += 1;
        } else if (evaluation.selectable) {
            alternativeCount += 1;
        } else {
            disabledCount += 1;
        }
        roomList.appendChild(room);
    });

    if (recommendationNote) {
        if (recommendedCount || alternativeCount) {
            recommendationNote.textContent = `Recommended for your stay: ${recommendedCount}. Alternative options: ${alternativeCount}. Unavailable / not possible: ${disabledCount}.`;
        } else {
            recommendationNote.textContent = 'No selectable rooms currently fit this party. Unavailable or impossible options remain visible with an explanation.';
        }
    }

    if (state.roomId) {
        const selectedCard = roomList.querySelector(`[data-room-id="${state.roomId}"]`);
        const selectedEvaluation = selectedCard ? evaluateRoomForGuests(selectedCard, state.adults, state.children) : null;
        if (!selectedCard || !selectedEvaluation?.selectable) {
            resetSelectedRoomState();
        } else {
            state.roomCount = selectedEvaluation.requiredRoomCount || 1;
            selectedCard.classList.add('selected');
            selectedCard.setAttribute('aria-pressed', 'true');
            const selectedButton = document.getElementById(`btn-room-${state.roomId}`);
            if (selectedButton) {
                selectedButton.textContent = state.roomCount > 1 ? `Selected x${state.roomCount}` : 'Selected';
                selectedButton.classList.add('is-selected');
            }
        }
    }
}

function syncCalendarFromManualInputs() {
    const checkInDisplay = document.getElementById('checkInDisplay');
    const checkOutDisplay = document.getElementById('checkOutDisplay');
    const checkInValue = parseManualDateInput(checkInDisplay?.value);
    const checkOutValue = parseManualDateInput(checkOutDisplay?.value);

    if (checkInDisplay?.value && !checkInValue) {
        setMessage('Please enter check-in in a valid format, for example 08 May 2026 or 2026-05-08.');
        scrollToMessage();
        return false;
    }

    if (checkOutDisplay?.value && !checkOutValue) {
        setMessage('Please enter check-out in a valid format, for example 11 May 2026 or 2026-05-11.');
        scrollToMessage();
        return false;
    }

    if (checkInValue && checkOutValue && !isValidDateRange(checkInValue, checkOutValue)) {
        setMessage('Check-out must be after check-in.');
        scrollToMessage();
        return false;
    }

    state.checkIn = checkInValue || '';
    state.checkOut = checkOutValue || '';
    document.getElementById('checkIn').value = state.checkIn;
    document.getElementById('checkOut').value = state.checkOut;

    if (calendarInstance) {
        if (state.checkIn && state.checkOut) {
            calendarInstance.setDate([state.checkIn, state.checkOut], true, 'Y-m-d');
        } else if (state.checkIn) {
            calendarInstance.setDate([state.checkIn], true, 'Y-m-d');
        } else {
            calendarInstance.clear();
        }
        updateMonthLabel(calendarInstance);
    }

    clearMessage();
    updateSummary();
    return true;
}

function updateSummary() {
    const roomStepDates = document.getElementById('room-step-dates');
    const roomStepSelected = document.getElementById('room-step-selected');
    const roomStepTotal = document.getElementById('room-step-total');

    state.checkIn = document.getElementById('checkIn').value;
    state.checkOut = document.getElementById('checkOut').value;
    state.adults = parseInt(document.getElementById('adults').value, 10);
    state.children = parseInt(document.getElementById('children').value, 10);
    const guestShapeChanged = ensureGuestStateShape();

    if (isValidDateRange(state.checkIn, state.checkOut)) {
        const d1 = new Date(`${state.checkIn}T12:00:00`);
        const d2 = new Date(`${state.checkOut}T12:00:00`);
        state.nights = Math.max(1, Math.round((d2 - d1) / (1000 * 60 * 60 * 24)));
    } else {
        state.nights = 1;
    }

    bookingState.room.totalPrice = getRoomSubtotal();

    if (roomStepDates) {
        roomStepDates.innerText = isValidDateRange(state.checkIn, state.checkOut)
            ? `${formatDisplayDate(state.checkIn)} - ${formatDisplayDate(state.checkOut)}`
            : 'Select dates';
    }
    if (roomStepSelected) roomStepSelected.innerText = bookingState.room.name ? getSelectedRoomLabel() : 'Choose a room';
    if (roomStepTotal) roomStepTotal.innerText = formatCurrency(getRoomSubtotal());

    if (guestShapeChanged && document.getElementById('step-3')?.classList.contains('active')) {
        renderGuestSections();
    }

    updateEnhancementSelectionUI();
    syncStayDisplay();
    updateDetailsSummary();
    updatePaymentSummary();
    updateRoomRecommendations();
    syncRoomAvailabilityForStay();
    updateStickyBookingCta();
}

function canSelectedRoomFitGuests() {
    const selectedCard = document.querySelector(`[data-room-id="${state.roomId}"]`);
    if (!selectedCard) return false;
    return evaluateRoomForGuests(selectedCard, state.adults, state.children).selectable;
}

function resetRoomSelectionUI() {
    document.querySelectorAll('.room-card').forEach((card) => {
        card.classList.remove('selected');
        card.setAttribute('aria-pressed', 'false');
    });

    document.querySelectorAll('.room-select-btn').forEach((btn) => {
        btn.innerText = 'Select room';
        btn.classList.remove('is-selected');
    });
}

function updateProgressNav(stepNum) {
    document.querySelectorAll('[data-step-nav]').forEach((el) => {
        const step = Number(el.dataset.stepNav);
        el.classList.remove('pending', 'current', 'completed');

        if (step < stepNum) {
            el.classList.add('completed');
            el.classList.add('is-clickable');
            el.setAttribute('aria-disabled', 'false');
        } else if (step === stepNum) {
            el.classList.add('current');
            el.classList.remove('is-clickable');
            el.setAttribute('aria-disabled', 'true');
        } else {
            el.classList.add('pending');
            el.classList.remove('is-clickable');
            el.setAttribute('aria-disabled', 'true');
        }
    });
}

function handleProgressStageNavigation(targetStep) {
    if (!targetStep || targetStep >= currentStep) return;
    clearMessage();
    showStep(targetStep);
    updateSummary();
}

async function checkForBookingUpdates() {
    const currentVersion = Number(document.body?.dataset.bookingVersion || 0);
    if (!currentVersion) return;

    try {
        const response = await fetch(`${buildBookingUrl('/api/booking-version')}?t=${Date.now()}`, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        if (!response.ok) return;

        const data = await response.json();
        const latestVersion = Number(data?.version || 0);
        if (latestVersion > currentVersion) {
            window.location.reload();
        }
    } catch (_error) {
        // Ignore transient polling failures during local development.
    }
}

function startBookingVersionWatcher() {
    if (bookingVersionPollStarted) return;
    bookingVersionPollStarted = true;

    window.setInterval(checkForBookingUpdates, 3000);
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            checkForBookingUpdates();
        }
    });
    window.addEventListener('focus', checkForBookingUpdates);
}

window.updateGuest = function(type, amt) {
    const el = document.getElementById(type + '-count');
    const hiddenId = type === 'child' ? 'children' : `${type}s`;
    const hidden = document.getElementById(hiddenId);
    let val = parseInt(hidden.value, 10) + amt;

    if (type === 'adult' && val < 1) val = 1;
    if (type === 'adult' && val > 6) val = 6;
    if (type === 'child' && val < 0) val = 0;
    if (type === 'child' && val > 4) val = 4;

    el.innerText = val;
    hidden.value = val;
    state[type + 's'] = val;
    clearMessage();
    updateSummary();
};

function selectRoom(id, name, price) {
    const card = document.querySelector(`[data-room-id="${id}"]`);
    const evaluation = card ? evaluateRoomForGuests(card, state.adults, state.children) : null;

    if (!card || !evaluation?.selectable) {
        setMessage(evaluation?.reason || `${name} is not available for the selected stay.`);
        scrollToMessage();
        return;
    }

    state.roomId = id;
    state.roomName = name;
    state.roomPrice = price;
    state.roomCount = evaluation.requiredRoomCount || 1;
    bookingState.room.description = card?.dataset.roomDescription || '';
    bookingState.room.image = card?.dataset.roomImage || '';

    resetRoomSelectionUI();

    card.classList.add('selected');
    card.setAttribute('aria-pressed', 'true');

    const btn = document.getElementById(`btn-room-${id}`);
    btn.innerText = state.roomCount > 1 ? `Selected x${state.roomCount}` : 'Selected';
    btn.classList.add('is-selected');

    clearMessage();
    updateSummary();
}

function validateStep(step) {
    if (step === 1) {
        if (!syncCalendarFromManualInputs()) {
            return false;
        }

        if (bookingFlow?.dataset.hasRooms !== 'true') {
            setMessage('There are no rooms available to reserve right now.');
            scrollToMessage();
            return false;
        }

        if (!state.checkIn || !state.checkOut) {
            setMessage('Please select both check-in and check-out dates.');
            scrollToMessage();
            return false;
        }

        if (!isValidDateRange(state.checkIn, state.checkOut)) {
            setMessage('Please choose a valid date range.');
            scrollToMessage();
            return false;
        }
    }

    if (step === 2) {
        if (!state.roomId) {
            setMessage('Please select a room.');
            scrollToMessage();
            return false;
        }

        if (!canSelectedRoomFitGuests()) {
            setMessage('Please select a room that fits the chosen number of adults and children.');
            scrollToMessage();
            return false;
        }
    }

    if (step === 3) {
        if (!validateDetailsStep()) {
            return false;
        }
    }

    if (step === 4) {
        if (!validatePaymentStep()) {
            return false;
        }
    }

    return true;
}

function nextStep(stepNum) {
    if (!validateStep(stepNum - 1)) return;
    clearMessage();
    showStep(stepNum);
    updateSummary();
}

function prevStep(stepNum) {
    showStep(stepNum);
}

function showStep(stepNum) {
    document.querySelectorAll('.step-content').forEach((el) => {
        el.classList.remove('active');
    });

    currentStep = stepNum;
    prepareStep(stepNum);

    setTimeout(() => {
        document.getElementById(`step-${stepNum}`).classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 50);

    updateProgressNav(stepNum);
    updateStickyBookingCta();
}

function formatReservationReference(reservationId) {
    return `#RES-${String(reservationId).padStart(4, '0')}`;
}

function formatDraftReference(value) {
    return `#DR-${String(value || '').slice(0, 8).toUpperCase() || 'PENDING'}`;
}

function renderApprovalState(data = {}) {
    const status = String(data.paymentStatus || 'PENDING').toUpperCase();
    bookingState.meta.approvalStatus = status;
    if (data.bookingDraftId) {
        setBookingDraftId(data.bookingDraftId);
    }
    if (data.publicToken) {
        setStatusToken(data.publicToken);
    }
    const draftReferenceToken = data.publicToken || bookingState.meta.statusToken || data.bookingDraftId || bookingState.meta.bookingDraftId;

    const titleEl = document.getElementById('approval-title');
    const copyEl = document.getElementById('approval-copy');
    const referenceLabelEl = document.getElementById('approval-reference-label');
    const statusEl = document.getElementById('approval-status');
    const referenceEl = document.getElementById('res-id');
    const roomEl = document.getElementById('res-room');
    const totalEl = document.getElementById('res-total');
    const iconShell = document.getElementById('approval-icon-shell');
    const iconEl = document.getElementById('approval-icon');
    const roomCount = Number(data.roomCount || 1);
    const roomLabel = data.roomName
        ? (roomCount > 1 ? `${data.roomName} x${roomCount}` : data.roomName)
        : '-';
    const totalLabel = data.pricingSnapshot?.formattedTotal || '$0';

    if (status === 'PAID') {
        if (titleEl) titleEl.textContent = 'Reservation Confirmed';
        if (copyEl) copyEl.textContent = 'Your iyzico payment was approved and your reservation is now confirmed.';
        if (referenceLabelEl) referenceLabelEl.textContent = 'Booking Reference';
        if (statusEl) statusEl.textContent = 'PAID';
        if (referenceEl) {
            referenceEl.textContent = data.reservationId
                ? formatReservationReference(data.reservationId)
                : formatDraftReference(draftReferenceToken);
        }
        if (iconShell) iconShell.className = 'w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-8';
        if (iconEl) {
            iconEl.className = 'material-symbols-outlined text-green-600 text-5xl';
            iconEl.textContent = 'check_circle';
        }
    } else if (status === 'FAILED') {
        if (titleEl) titleEl.textContent = 'Payment Failed';
        if (copyEl) copyEl.textContent = 'We could not confirm your payment. You can return to the booking flow and try again.';
        if (referenceLabelEl) referenceLabelEl.textContent = 'Draft Reference';
        if (statusEl) statusEl.textContent = 'FAILED';
        if (referenceEl) referenceEl.textContent = formatDraftReference(draftReferenceToken);
        if (iconShell) iconShell.className = 'w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-8';
        if (iconEl) {
            iconEl.className = 'material-symbols-outlined text-red-600 text-5xl';
            iconEl.textContent = 'error';
        }
    } else {
        if (titleEl) titleEl.textContent = 'Payment Pending';
        if (copyEl) copyEl.textContent = 'Your payment is still being processed. Refresh this page in a moment for the latest approval status.';
        if (referenceLabelEl) referenceLabelEl.textContent = 'Draft Reference';
        if (statusEl) statusEl.textContent = 'PENDING';
        if (referenceEl) referenceEl.textContent = formatDraftReference(draftReferenceToken);
        if (iconShell) iconShell.className = 'w-24 h-24 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-8';
        if (iconEl) {
            iconEl.className = 'material-symbols-outlined text-amber-600 text-5xl';
            iconEl.textContent = 'schedule';
        }
    }

    if (roomEl) roomEl.textContent = roomLabel;
    if (totalEl) totalEl.textContent = totalLabel;
}

async function createOrUpdateBookingDraft() {
    const response = await fetch(buildBookingUrl('/api/booking-drafts'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            bookingDraftId: bookingState.meta.bookingDraftId || undefined,
            draft: buildBookingDraftPayload()
        })
    });

    const data = await response.json().catch(() => ({
        success: false,
        error: 'Unexpected server response.'
    }));

    if (!response.ok || !data.success) {
        throw new Error(data.error || 'Booking draft could not be created.');
    }

    setBookingDraftId(data.bookingDraftId);
    setStatusToken(data.publicToken);
    bookingState.meta.approvalStatus = data.paymentState?.status || 'PENDING';
    return data;
}

async function initializeHostedPaymentCheckout(bookingDraftId) {
    const response = await fetch(buildBookingUrl('/api/payments/iyzico/initialize'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ bookingDraftId })
    });

    const data = await response.json().catch(() => ({
        success: false,
        error: 'Unexpected server response.'
    }));

    if (!response.ok || !data.success) {
        throw new Error(data.error || 'Secure payment could not be initialized.');
    }

    return data;
}

async function loadApprovalStatus(statusToken) {
    const response = await fetch(buildBookingUrl(`/api/booking-drafts/status/${encodeURIComponent(statusToken)}`), {
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache'
        }
    });

    const data = await response.json().catch(() => ({
        success: false,
        error: 'Unexpected server response.'
    }));

    if (!response.ok || !data.success) {
        throw new Error(data.error || 'Approval status could not be loaded.');
    }

    renderApprovalState(data);
    return data;
}

async function submitReservation() {
    if (!validateStep(4)) return;

    const btn = document.getElementById('sticky-cta-button');
    clearMessage();
    ctaProcessing = true;
    updateSummary();
    btn.disabled = true;
    btn.innerText = 'Redirecting...';

    try {
        const draft = await createOrUpdateBookingDraft();
        const payment = await initializeHostedPaymentCheckout(draft.bookingDraftId);
        setMessage('Redirecting to iyzico secure payment...', 'info');
        if (!payment.paymentPageUrl) {
            throw new Error('iyzico payment page URL is missing.');
        }
        window.location.assign(payment.paymentPageUrl);
        return;
    } catch (_error) {
        setMessage('Secure payment could not be started. Please try again.');
        scrollToMessage();
        ctaProcessing = false;
        btn.disabled = false;
        updateStickyBookingCta();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const calendarEl = document.getElementById('inline-calendar');
    if (!calendarEl) return;

    startBookingVersionWatcher();

    const checkInDisplay = document.getElementById('checkInDisplay');
    const checkOutDisplay = document.getElementById('checkOutDisplay');

    calendarInstance = flatpickr('#inline-calendar', {
        inline: true,
        mode: 'range',
        minDate: 'today',
        showMonths: 1,
        dateFormat: 'Y-m-d',
        prevArrow: '',
        nextArrow: '',
        onChange: function(selectedDates, dateStr, instance) {
            const checkInInput = document.getElementById('checkIn');
            const checkOutInput = document.getElementById('checkOut');

            if (selectedDates.length >= 1) {
                state.checkIn = instance.formatDate(selectedDates[0], 'Y-m-d');
                checkInInput.value = state.checkIn;
            } else {
                state.checkIn = '';
                checkInInput.value = '';
            }

            if (selectedDates.length === 2) {
                state.checkOut = instance.formatDate(selectedDates[1], 'Y-m-d');
                checkOutInput.value = state.checkOut;
                const diffTime = selectedDates[1] - selectedDates[0];
                state.nights = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
            } else {
                state.checkOut = '';
                checkOutInput.value = '';
                state.nights = 1;
            }

            clearMessage();
            updateSummary();
        },
        onMonthChange: function(selectedDates, dateStr, instance) {
            updateMonthLabel(instance);
        },
        onYearChange: function(selectedDates, dateStr, instance) {
            updateMonthLabel(instance);
        },
        onReady: function(selectedDates, dateStr, instance) {
            updateMonthLabel(instance);
            updateSummary();
        }
    });

    [checkInDisplay, checkOutDisplay].forEach((input) => {
        if (!input) return;

        input.addEventListener('input', () => {
            const formatted = normalizeDateInputDigits(input.value);
            if (input.value !== formatted) {
                input.value = formatted;
            }
        });
        input.addEventListener('blur', syncCalendarFromManualInputs);
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                input.blur();
            }
        });
    });

    const prevBtn = document.getElementById('custom-prev-month');
    const nextBtn = document.getElementById('custom-next-month');
    if (prevBtn) prevBtn.addEventListener('click', () => calendarInstance.changeMonth(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => calendarInstance.changeMonth(1));

    document.querySelectorAll('[data-step-nav]').forEach((stage) => {
        stage.addEventListener('click', () => {
            handleProgressStageNavigation(Number(stage.dataset.stepNav));
        });

        stage.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            handleProgressStageNavigation(Number(stage.dataset.stepNav));
        });
    });

    const stickyCtaButton = document.getElementById('sticky-cta-button');
    if (stickyCtaButton) {
        stickyCtaButton.addEventListener('click', handleStickyCtaClick);
    }

    document.querySelectorAll('[data-room-card]').forEach((card) => {
        card.addEventListener('click', () => {
            selectRoom(
                Number(card.dataset.roomId),
                card.dataset.roomName || '',
                card.dataset.roomPrice || 0
            );
        });

        card.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            selectRoom(
                Number(card.dataset.roomId),
                card.dataset.roomName || '',
                card.dataset.roomPrice || 0
            );
        });

        const button = card.querySelector('[data-room-select-button]');
        if (button) {
            button.addEventListener('click', (event) => {
                event.stopPropagation();
                selectRoom(
                    Number(card.dataset.roomId),
                    card.dataset.roomName || '',
                    card.dataset.roomPrice || 0
                );
            });
        }
    });

    const detailsStep = document.getElementById('step-3');
    if (detailsStep) {
        detailsStep.addEventListener('input', (event) => {
            const field = event.target.closest('[data-field-key]');
            if (!field || !field.dataset.fieldKey.startsWith('details.')) return;

            syncFieldIntoBookingState(field);
            clearFieldError(field.dataset.fieldKey);

            if (bookingState.details.usePrimaryGuestForAdult1 && field.dataset.fieldKey.startsWith('details.primaryGuest.')) {
                syncPrimaryGuestToAdultOne();
                renderGuestSections();
            }

            if (bookingState.details.usePrimaryGuestForAdult1 && (
                field.dataset.fieldKey === 'details.adultGuests.0.firstName'
                || field.dataset.fieldKey === 'details.adultGuests.0.lastName'
            )) {
                const primaryField = field.dataset.fieldKey.endsWith('firstName')
                    ? bookingState.details.primaryGuest.firstName
                    : bookingState.details.primaryGuest.lastName;

                if (field.value.trim() !== primaryField.trim()) {
                    bookingState.details.usePrimaryGuestForAdult1 = false;
                    const checkbox = document.getElementById('usePrimaryForAdult1');
                    if (checkbox) checkbox.checked = false;
                }
            }

            updateSummary();
        });

        detailsStep.addEventListener('change', (event) => {
            const field = event.target.closest('[data-field-key]');
            if (field && field.dataset.fieldKey.startsWith('details.')) {
                syncFieldIntoBookingState(field);
                clearFieldError(field.dataset.fieldKey);
            }

            if (event.target.id === 'usePrimaryForAdult1') {
                bookingState.details.usePrimaryGuestForAdult1 = event.target.checked;
                if (bookingState.details.usePrimaryGuestForAdult1) {
                    syncPrimaryGuestToAdultOne();
                }
                renderGuestSections();
            }

            updateSummary();
        });

        detailsStep.addEventListener('click', (event) => {
            const enhancementButton = event.target.closest('[data-enhancement-key]');
            if (!enhancementButton) return;

            const enhancementKey = enhancementButton.dataset.enhancementKey;
            bookingState.details.enhancements[enhancementKey] = !bookingState.details.enhancements[enhancementKey];
            updateEnhancementSelectionUI();
            updateSummary();
        });
    }

    const paymentStep = document.getElementById('step-4');
    if (paymentStep) {
        paymentStep.addEventListener('input', (event) => {
            const field = event.target.closest('[data-field-key]');
            if (!field || !field.dataset.fieldKey.startsWith('payment.')) return;
            syncFieldIntoBookingState(field);
            clearFieldError(field.dataset.fieldKey);
            updateSummary();
        });

        paymentStep.addEventListener('change', (event) => {
            if (event.target.matches('input[name="paymentMethod"]')) {
                bookingState.payment.method = event.target.value;
                clearFieldError('payment.method');
                updatePaymentMethodUI();
                updateSummary();
                return;
            }

            const field = event.target.closest('[data-field-key]');
            if (!field || !field.dataset.fieldKey.startsWith('payment.')) return;
            syncFieldIntoBookingState(field);
            clearFieldError(field.dataset.fieldKey);
            updateSummary();
        });
    }

    const queryParams = getQueryParams();
    const initialBookingDraftId = queryParams.get('bookingDraftId') || getStoredBookingDraftId();
    const initialStatusToken = queryParams.get('statusToken') || getStoredStatusToken();
    if (initialBookingDraftId) {
        setBookingDraftId(initialBookingDraftId);
    }
    if (initialStatusToken) {
        setStatusToken(initialStatusToken);
    }

    ensureGuestStateShape();
    updateSummary();

    if (queryParams.get('step') === '5') {
        renderApprovalState({
            publicToken: initialStatusToken,
            paymentStatus: 'PENDING',
            roomName: bookingState.room.name,
            roomCount: bookingState.room.roomCount,
            pricingSnapshot: {
                formattedTotal: formatCurrency(getGrandTotal())
            }
        });
        showStep(5);

        if (initialStatusToken) {
            loadApprovalStatus(initialStatusToken).catch(() => {
                renderApprovalState({
                    publicToken: initialStatusToken,
                    paymentStatus: 'FAILED',
                    roomName: bookingState.room.name,
                    roomCount: bookingState.room.roomCount,
                    pricingSnapshot: {
                        formattedTotal: formatCurrency(getGrandTotal())
                    }
                });
            });
        }
        return;
    }

    showStep(1);
});
