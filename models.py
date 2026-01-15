from __future__ import annotations

from datetime import date
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from Cadastro_Brasil_Risk.validators import normalize_name, normalize_cpf, normalize_cep, normalize_phone, only_digits

Genero = Literal["Masculino", "Feminino", "Outros"]
Funcao = Literal["Motorista", "Ajudante"]
Perfil = Literal["Agregado"]

VehicleCategory = Literal["Aluguel", "Particular"]
VehicleOwnerType = Literal["Juridica", "Fisica"]

class DriverData(BaseModel):
    # Upload
    cnh_path: Optional[str] = None  # path to temp file

    # Personal
    nome: str
    genero: Genero
    data_nascimento: date
    cpf: str
    rg: str
    data_emissao: date
    orgao_exp: str
    nome_pai: Optional[str] = None
    nome_mae: str

    funcao: Funcao
    perfil: Perfil = "Agregado"

    empresa_centro_custo: str = "FEDEX"
    responsavel_faturamento: str = "FEDEX BRASIL"

    # Address
    cep: str
    uf: str
    cidade: str
    bairro: str
    logradouro: str
    numero: str
    complemento: Optional[str] = None

    # Contact
    telefone: Optional[str] = None
    celular: str
    telefone_comercial: Optional[str] = None
    email: Optional[str] = None

    # CNH
    cnh_registro: str
    cnh_numero: str
    cnh_categoria: str
    cnh_validade: date
    cnh_uf: str

    @field_validator("nome", "nome_pai", "nome_mae")
    @classmethod
    def _norm_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        vv = normalize_name(v)
        return vv

    @field_validator("cpf")
    @classmethod
    def _norm_cpf(cls, v: str) -> str:
        vv = normalize_cpf(v)
        if len(vv) != 11:
            raise ValueError("CPF deve ter 11 dígitos.")
        return vv

    @field_validator("cep")
    @classmethod
    def _norm_cep(cls, v: str) -> str:
        vv = normalize_cep(v)
        if len(vv) != 8:
            raise ValueError("CEP deve ter 8 dígitos.")
        return vv

    @field_validator("celular", "telefone", "telefone_comercial")
    @classmethod
    def _norm_phones(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        vv = normalize_phone(v)
        if len(vv) < 10:
            raise ValueError("Telefone/Celular deve ter ao menos 10 dígitos (DDD + número).")
        return vv

    @field_validator("rg", "numero", "cnh_registro", "cnh_numero")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        vv = only_digits(v)
        if not vv:
            raise ValueError("Campo numérico inválido.")
        return vv

class VehicleOwnerJuridica(BaseModel):
    owner_type: Literal["Juridica"] = "Juridica"
    cnpj: str
    inscricao_estadual: str
    uf: str
    razao_social: str

    @field_validator("cnpj", "inscricao_estadual")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        return only_digits(v)

    @field_validator("razao_social")
    @classmethod
    def _norm_name(cls, v: str) -> str:
        return v.strip()

class VehicleOwnerFisica(BaseModel):
    owner_type: Literal["Fisica"] = "Fisica"
    cpf: str
    rg: str
    uf: str
    nome: str
    data_nascimento: date
    nome_mae: str
    celular: str

    @field_validator("cpf")
    @classmethod
    def _norm_cpf(cls, v: str) -> str:
        vv = normalize_cpf(v)
        if len(vv) != 11:
            raise ValueError("CPF do proprietário deve ter 11 dígitos.")
        return vv

    @field_validator("rg")
    @classmethod
    def _digits_rg(cls, v: str) -> str:
        return only_digits(v)

    @field_validator("nome", "nome_mae")
    @classmethod
    def _norm_names(cls, v: str) -> str:
        return normalize_name(v)

    @field_validator("celular")
    @classmethod
    def _norm_phone(cls, v: str) -> str:
        vv = normalize_phone(v)
        if len(vv) < 10:
            raise ValueError("Celular do proprietário deve ter ao menos 10 dígitos.")
        return vv

VehicleOwner = Union[VehicleOwnerJuridica, VehicleOwnerFisica]

class VehicleData(BaseModel):
    placa: str
    tipo_veiculo: str  # label (3/4, Carro, Motocicleta, Pick-up, Utilitário, Van)
    chassi: str
    ano_fabricacao: str
    marca: str
    modelo: str
    cor: str
    renavam: str
    uf: str
    cidade: str
    perfil: Perfil = "Agregado"
    empresa_centro_custo: str = "FEDEX"
    data_licenciamento: Optional[date] = None

    categoria: VehicleCategory
    rntrc: Optional[str] = None
    rntrc_validade: Optional[str] = None  # could be date, kept string for MVP
    empresa: str = "FEDEX BRASIL"

    proprietario: VehicleOwner

    equip_rastreamento: str = "Não Possui"

    @field_validator("placa")
    @classmethod
    def _norm_placa(cls, v: str) -> str:
        vv = (v or "").strip().upper()
        if len(vv) < 6:
            raise ValueError("Placa inválida.")
        return vv

    @field_validator("ano_fabricacao", "renavam")
    @classmethod
    def _digits(cls, v: str) -> str:
        vv = only_digits(v)
        if not vv:
            raise ValueError("Campo numérico inválido.")
        return vv

    @field_validator("chassi")
    @classmethod
    def _trim(cls, v: str) -> str:
        return (v or "").strip()

class CourierRequest(BaseModel):
    with_vehicle: bool
    driver: DriverData
    vehicle: Optional[VehicleData] = None

    @field_validator("vehicle")
    @classmethod
    def _vehicle_required_if_with_vehicle(cls, v: Optional[VehicleData], info):
        with_vehicle = info.data.get("with_vehicle")
        if with_vehicle and v is None:
            raise ValueError("Vehicle é obrigatório quando with_vehicle=True.")
        return v

class Job(BaseModel):
    id: int
    request_id: int
    job_type: Literal["STEP1_DRIVER", "STEP2_VEHICLE"]
    status: Literal["PENDING", "QUEUED", "RUNNING", "DONE", "FAILED", "BLOCKED"]
    attempts: int = 0
    last_error: Optional[str] = None
    log: str = ""
