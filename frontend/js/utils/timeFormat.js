const CHINESE_DATE_TIME_RE = /^\d{4}年\d{1,2}月\d{1,2}日\d{2}点\d{2}分$/;
const ISO_DATE_TIME_RE = /^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?$/;
const LOCAL_DATE_TIME_RE = /^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?$/;

function pad2(value) {
    return String(value).padStart(2, '0');
}

function parseDisplayDateTime(value) {
    if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
    const text = String(value || '').trim();
    if (!text || CHINESE_DATE_TIME_RE.test(text) || !ISO_DATE_TIME_RE.test(text)) return null;

    const localMatch = text.match(LOCAL_DATE_TIME_RE);
    if (localMatch) {
        const [, year, month, day, hour, minute, second = '0'] = localMatch;
        return new Date(
            Number(year),
            Number(month) - 1,
            Number(day),
            Number(hour),
            Number(minute),
            Number(second),
        );
    }

    const normalized = text.includes(' ') ? text.replace(' ', 'T') : text;
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDisplayDateTime(value) {
    if (value === null || value === undefined) return '';
    const original = String(value).trim();
    if (!original || CHINESE_DATE_TIME_RE.test(original)) return original;

    const date = parseDisplayDateTime(value);
    if (!date) return original;

    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日${pad2(date.getHours())}点${pad2(date.getMinutes())}分`;
}

export function formatCurrentDisplayDateTime() {
    return formatDisplayDateTime(new Date());
}

export default formatDisplayDateTime;
