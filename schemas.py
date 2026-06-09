from pydantic import BaseModel, field_validator
from typing import List, Optional

# ---------- Вспомогательные модели для участников ДТП ----------
class TsUch(BaseModel):
    n_uch: str
    kt_uch: str
    s_sm: str
    pol: str
    s_t: str
    npdd: List[str]
    sop_npdd: List[str]
    safety_belt: str
    s_seat_group: str
    alco: str
    v_st: str

# ---------- Модель транспортного средства ----------
class TsInfo(BaseModel):
    n_ts: str
    ts_s: str
    t_ts: str
    m_ts: str
    marka_ts: str
    color: strdata
    m_pov: str
    t_n: str
    r_rul: str
    g_v: str
    o_pf: str
    ts_uch: List[TsUch]

# ---------- Условия дороги (dor_usl) ----------
class DorUsl(BaseModel):
    sdor: List[str]
    obj_dtp: List[str]
    ndu: List[str]
    factor: List[str]
    spog: List[str]
    s_pch: str
    osv: str
    chom: str

# ---------- Основная информация о ДТП (info_dtp) ----------
class InfoDtp(BaseModel):
    empt_number: str
    date_dtp: str
    time: str
    coord_w: float
    coord_l: float
    dtpv: str
    k_ts: int
    k_uch: int
    pog: int
    ran: int
    s_dtp: str
    district: str
    house: str
    km: str
    m: str
    np: str
    street: str
    dor: str
    dor_z: str
    dor_k: str
    k_ul: str
    dor_usl: DorUsl
    ts_info: List[TsInfo]
    uch_info: List  # в примере всегда пустой список, тип можно уточнить при необходимости

# ---------- Карточка ДТП (dtpcardlist) ----------
class DtpCardList(BaseModel):
    info_dtp: List[InfoDtp]

# ---------- Результат по одному показателю (result) ----------
class ResultItem(BaseModel):
    countcard: int
    pog_v: int
    ran_v: int
    dtpcardlist: DtpCardList

# ---------- Показатель (pok_list) ----------
class PokItem(BaseModel):
    pok_code: int
    pok_name: str
    result: List[ResultItem]  # временно список

    @field_validator('result', mode='after')
    @classmethod
    def check_and_unpack(cls, v: List[ResultItem]) -> ResultItem:
        if len(v) != 1:
            raise ValueError(f'result должен содержать ровно 1 элемент, получено {len(v)}')
        return v[0]  # теперь result становится одиночным объектом

    # TODO Написать тест на проверку условия len != 1

# ---------- Регион (region_list) ----------
class RegionItem(BaseModel):
    reg_code: int
    reg_name: str
    pok_list: List[PokItem]

# ---------- Результаты (results) ----------
class Results(BaseModel):
    date: str
    region_list: List[RegionItem]

# ---------- Запрос (request) ----------
class RequestInfo(BaseModel):
    dat: str
    reg: str
    pok: str

# ---------- Корневая модель ----------
class Root(BaseModel):
    status: int
    request: RequestInfo
    id: int
    entityname: str
    results: Results