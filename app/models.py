"""
Definition of models.
"""

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from uuid import uuid4

# Create your models here.
class CustomUser(AbstractUser):
    id = models.AutoField(primary_key=True, unique=True)
    session_token = models.TextField()


class ShieldController(models.IntegerChoices):
    NONE = 0, "None"
    BUBBLE = 1, "Bubble"
    FRONTBACK = 2, "FrontBack"
    QUADRANT = 3, "Quadrant"
    
    @property
    def num_faces(self):
        if self == self.BUBBLE:
            return 1
        elif self == self.FRONTBACK:
            return 2
        elif self == self.QUADRANT:
            return 4
        else:
            return 0

    @property
    def controller_type(self):
        return self.label


class ShipModel(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=64, null=True)
    size = models.IntegerField(null=True)
    shield_faces = models.IntegerField(choices=ShieldController.choices, null=True)
    pitch_rate = models.IntegerField(null=True)
    scm_speed = models.FloatField(null=True)
    total_hp = models.IntegerField(null=True)
    vital_hull_hp = models.IntegerField(null=True)
    vital_hull_name = models.CharField(max_length=64, null=True)
    visible_hull_area = models.FloatField(null=True)
    ballistic_resistance = models.FloatField(null=True)
    energy_resistance = models.FloatField(null=True)
    distortion_resistance = models.FloatField(null=True)
    max_weapon_power = models.IntegerField(null=True)
    raw_data = models.JSONField(null=True)


    @classmethod
    def from_json_object(cls, source:dict):
        instance = cls()
        instance.name = source["localName"]

        data = source["data"]
        instance.raw_data = data
        instance.size = data["size"]
        instance.max_weapon_power = data["rnPowerPools"].get("weaponGun", {}).get("poolSize", None)
        shield_type = data.get("shield", {}).get("faceType", "None")
        if shield_type == "Bubble": 
            num = 1
        elif shield_type == "FrontBack":
            num = 2
        elif shield_type == "Quadrant":
            num = 3
        else:
            num = 0
        instance.shield_faces = ShieldController(num)

        vhp:int = 0
        vname:str = ""

        for part in data["hull"]["hp"]:
            if int(part["hp"]) > vhp:
                vhp = int(part["hp"])
                vname = str(part["name"])

        if vhp > 0:
            instance.vital_hull_hp = vhp
            instance.vital_hull_name = vname
            instance.total_hp = data.get("hull", {}).get("totalHp", vhp)

        armor:dict = data.get("armor", {}).get("data", {}).get("armor", {}).get("damageMultiplier", {})

        instance.ballistic_resistance = armor.get("damagePhysical", 0)
        instance.energy_resistance = armor.get("damageEnergy", 0)
        instance.distortion_resistance = armor.get("damageDistortion", 0)

        instance.pitch_rate = data.get("ifcs", {}).get("angularVelocity", {}).get("x", 0)
        instance.scm_speed = data.get("ifcs", {}).get("scmSpeed", 0)
        dimensions = sorted(data.get("vehicle", {}).get("size", {}).values())
        if len(dimensions) >= 2:
            instance.visible_hull_area = dimensions[-1] * dimensions[-2]
        else:
            instance.visible_hull_area = 100
        
        return instance



class WeaponModel(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=64, null=True)
    size = models.IntegerField(null=True)
    fire_rate = models.IntegerField(null=True)
    ammo_count = models.IntegerField(null=True)
    spread = models.FloatField(null=True)
    alpha_damage = models.FloatField(null=True)
    damage_type = models.CharField(choices=settings.DAMAGE_TYPES, max_length=32, null=True)
    projectile_speed = models.IntegerField(null=True)
    burst_duration = models.IntegerField(null=True)
    burst_cooldown = models.IntegerField(null=True)
    burst_dps = models.FloatField(null=True)
    total_runtime = models.FloatField(null=True)
    sustained_dps = models.FloatField(null=True)
    raw_data = models.JSONField(null=True)

    @classmethod
    def from_json_object(cls, source:dict):
        instance = cls()

        instance.raw_data = source
        instance.name = source["localName"]
        data = source["data"]
        instance.size = data["size"]
        instance.fire_rate = data["weapon"]["fireActions"].get("fireRate", 10) / 60
        instance.spread = data["weapon"].get("spread", {"max": 0.5})["max"]
        instance.projectile_speed = data["ammo"]["data"]["speed"]
        instance.ammo_count = data.get("ammoContainer", {}).get("maxAmmoCount", 0)

        alpha_damages:dict = data["ammo"]["data"]["damage"]
        if instance.ammo_count == 0:
            if alpha_damages.get("damageEnergy", 0) > 0:
                instance.damage_type = settings.DAMAGE_TYPES[1][1]
                instance.alpha_damage = alpha_damages["damageEnergy"]

            elif alpha_damages.get("damageDistortion", 0) > 0:
                instance.damage_type = settings.DAMAGE_TYPES[2][1]
                instance.alpha_damage = alpha_damages["damageDistortion"]

            
            max_capacitor_load:int = data["weapon"]["regen"]["maxAmmoLoad"]
            max_regen_rps:float = data["weapon"]["regen"]["maxRegenPerSec"]

            instance.burst_duration = max_capacitor_load / instance.fire_rate
            instance.burst_cooldown = max_capacitor_load / max_regen_rps
            instance.total_runtime = 1000.0
            instance.burst_dps = instance.alpha_damage * instance.fire_rate

        else:
            instance.damage_type = settings.DAMAGE_TYPES[0][1]
            instance.alpha_damage = alpha_damages["damagePhysical"]

            heat_data:dict = data["weapon"]["connection"].get("simplifiedHeat", {"overheatTemperature": 1,
                                                                                   "minTemperature": 0,
                                                                                   "timeTillCoolingStarts": 0,
                                                                                   "overheatFixTime": 0})
            overheat_temp:int = heat_data["overheatTemperature"] - heat_data["minTemperature"]
            cooldown_time:int = heat_data["timeTillCoolingStarts"] + heat_data["overheatFixTime"]
            heat_gen_per_second:float = data["weapon"]["fireActions"]["heatPerShot"] * instance.fire_rate

            if heat_gen_per_second == 0:
                instance.burst_duration = 99999
            else:
                instance.burst_duration = overheat_temp / heat_gen_per_second

            instance.burst_cooldown = cooldown_time
            instance.total_runtime = (((instance.ammo_count / instance.fire_rate) / instance.burst_duration) * instance.burst_cooldown) + (instance.ammo_count / instance.fire_rate)
            instance.burst_dps = instance.alpha_damage * instance.fire_rate

        return instance



class ShieldModel(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=64, null=True)
    total_hp = models.IntegerField(null=True)
    size = models.IntegerField(null=True)
    max_power_slots = models.IntegerField(null=True)
    min_power_slots = models.IntegerField(null=True)
    min_ballistic_resistance = models.FloatField(null=True)
    max_ballistic_resistance = models.FloatField(null=True)
    min_energy_resistance = models.FloatField(null=True)
    max_energy_resistance = models.FloatField(null=True)
    min_distortion_resistance = models.FloatField(null=True)
    max_distortion_resistance = models.FloatField(null=True)
    min_ballistic_absorption = models.FloatField(null=True)
    max_ballistic_absorption = models.FloatField(null=True)
    min_energy_absorption = models.FloatField(null=True)
    max_energy_absorption = models.FloatField(null=True)
    min_distortion_absorption = models.FloatField(null=True)
    max_distortion_absorption = models.FloatField(null=True)
    raw_data = models.JSONField(null=True)

    @classmethod
    def from_json_object(cls, source:dict):
        instance = cls()
        instance.raw_data = source
        instance.name = source["localName"]
        data = source["data"]
        instance.total_hp = data["shield"]["maxShieldHealth"]
        instance.size = data["size"]
        instance.max_power_slots = data["resource"]["online"]["consumption"]["powerSegment"]
        instance.min_power_slots = instance.max_power_slots * data["resource"].get("conversionMinimumFraction", 1)
        instance.max_ballistic_resistance = data["shield"]["resistance"]["physicalMax"]
        instance.min_ballistic_resistance = data["shield"]["resistance"]["physicalMin"]
        instance.max_energy_resistance = data["shield"]["resistance"]["energyMax"]
        instance.min_energy_resistance = data["shield"]["resistance"]["energyMin"]
        instance.max_distortion_resistance = data["shield"]["resistance"]["distortionMax"]
        instance.min_distortion_resistance = data["shield"]["resistance"]["distortionMin"]
        instance.max_ballistic_absorption = data["shield"]["absorption"]["physicalMax"]
        instance.min_ballistic_absorption = data["shield"]["absorption"]["physicalMin"]
        instance.max_energy_absorption = data["shield"]["absorption"]["energyMax"]
        instance.min_energy_absorption = data["shield"]["absorption"]["energyMin"]
        instance.max_distortion_absorption = data["shield"]["absorption"]["distortionMax"]
        instance.min_distortion_absorption = data["shield"]["absorption"]["distortionMin"]
        
        return instance


class LoadoutModel(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loadouts", null=True)
    identifier = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=64, null=True)
    ship_name = models.CharField(max_length=64, null=True)
    weapons_power_percentage = models.FloatField(null=True)
    shields_power_percentage = models.FloatField(null=True)
    weapons = models.JSONField(null=True)
    shields = models.JSONField(null=True)
    raw_data = models.JSONField(null=True)

    @classmethod
    def from_json_object(cls, data:dict):
        instance = cls()
        instance.raw_data = data
        instance.name = data["name"]
        instance.identifier = data.get("shortened", data.get("identifier", str(uuid4())))
        instance.ship_name = data["loadout"]["ship"]["localName"]

        items:list[dict] = data["loadout"]["loadout"]
        weapon_power_available:int = 0
        weapon_power_assigned:int = 0
        shield_power_available:int = 0
        shield_power_assigned:int = 0

        for slot in data["loadout"].get("segmentConfiguration", {}).get("weapon", []):
            if not slot["disabled"]:
                weapon_power_available += slot["number"]
                if slot["selected"]:
                    weapon_power_assigned += slot["number"]
        for slot in data["loadout"].get("segmentConfiguration", {}).get("shield", []):
            if not slot["disabled"]:
                shield_power_available += slot["number"]
                if slot["selected"]:
                    shield_power_assigned += slot["number"]

        if 0 not in [weapon_power_available, shield_power_available]:
            instance.weapons_power_percentage = weapon_power_assigned / weapon_power_available
            instance.shields_power_percentage = shield_power_assigned / shield_power_available 
        else:
            if weapon_power_available != 0:
                instance.weapons_power_percentage = weapon_power_assigned / weapon_power_available
            else:
                instance.weapons_power_percentage = 1

            if shield_power_available != 0:
                instance.shields_power_percentage = shield_power_assigned / shield_power_available
            else:
                instance.shields_power_percentage = 1

        operator_counter = 1
        weapons_dict = {"pilot": []}
        shields_list = []
        for item in items:
            if item.get("card") == "turrets":
                if len(item["loadout"]) > 0:
                    name = f"Turret {operator_counter}"
                    weapons_dict[name] = []
                    operator_counter += 1

                    for i in item["loadout"]:
                        if "TractorBeam" in [item_type["type"] for item_type in i["itemTypes"]]:
                            continue
                        elif i["item"]["calculatorType"] == "mount":
                            mounted_weapons = i["loadout"]
                            for weapon in mounted_weapons:
                                if weapon["item"]["calculatorType"] == "weapon":
                                    weapon_name = weapon["item"]["localName"]
                                    weapons_dict[name].append(weapon_name)
                                    
                        elif i["item"]["calculatorType"] == "weapon":
                            weapon_name = i["item"]["localName"]
                            weapons_dict[name].append(weapon_name)

            if item.get("card") == "weapons":
                if item["item"]["calculatorType"] in ["mount", "turret"]:
                    mounted_weapons = item["loadout"]
                    for weapon in mounted_weapons:
                        if "TractorBeam" in [item_type["type"] for item_type in weapon["itemTypes"]]:
                            continue
                        elif weapon["item"]["calculatorType"] == "weapon":
                            weapon_name = weapon["item"]["localName"]
                            weapons_dict["pilot"].append(weapon_name)

                elif item["item"]["calculatorType"] == "weapon" and item["item"]["localName"]:
                    weapon_name = weapon["item"]["localName"]
                    weapons_dict["pilot"].append(weapon_name)

            if item.get("card") == "shields":
                shield_name = item["item"]["localName"]
                shields_list.append(shield_name)

        instance.weapons = weapons_dict
        instance.shields = shields_list

        return instance
