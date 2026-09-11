<template>
  <span
    class="cartoon-avatar"
    role="img"
    :aria-label="`${label}的卡通头像`"
    :style="{
      backgroundImage: `url(${avatarSheet})`,
      backgroundPosition: `${(index % 4) * 33.333}% ${Math.floor(index / 4) * 100}%`,
    }"
  />
</template>

<script setup>
import avatarSheet from "../assets/avatars/pixel-avatar-sheet.png";

defineProps({
  index: { type: Number, default: 0 },
  label: { type: String, default: "成员" },
});
</script>

<style scoped>
.cartoon-avatar {
  display: block;
  flex: 0 0 auto;
  border: 2px solid #fff;
  border-radius: 50%;
  background-repeat: no-repeat;
  background-size: 400% 200%;
  box-shadow: 0 1px 4px rgba(31, 48, 67, .18);
}
</style>
